"""Run with Python Playwright and Chromium. All records live in isolated browser contexts."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import shutil
import json
import subprocess

SOURCE = Path(__file__).resolve().parents[1] / 'index.html'
URL = 'http://localhost:9831/'
source = SOURCE.read_text()
# Expose fixture builders inside the closure only in the test response.
marker = 'window.RoseachySmartSync=api;'
assert source.count(marker) == 1
fixtures = '''window.fixture={
 credit:CreditAccounts,supplierBalance:()=>supplierDebtModel(true).totalK/100,
 supplierInvoice:()=>inventoryCommit(()=>{
   const m=getMarketState(),ts=nowIso();m.suppliers.push({id:'test-supplier',name:'Supply Co',createdAt:ts});
   const t={id:'invoice-line',type:'purchase_credit',domain:'retail',refKind:'product',productId:'soap',productName:'Soap',qty:50,amount:100,unitPrice:2,ts,
    supplierId:'test-supplier',marketGroupPurchaseId:'invoice',supplierPurchaseId:'invoice',marketPurchaseId:'item'};
   m.marketPurchases.push({id:'invoice',supplierId:t.supplierId,total:100,items:[{productId:'soap',marketPurchaseId:'item',txId:t.id,qty:50,total:100}],payments:[],completedAt:ts});
   setMarketState(m);if(!applyEffect(t,false,true))throw Error('Purchase movement failed');tx.push(t);return true;
 },'Market Desk'),openPayment:()=>openSupplierPayment('invoice'),backup:roseachySafeBackup,trust:SyncPrivacy.trust,stock:getStock,tx:()=>tx,
 seed:()=>RS.atomic(()=>setStock([{id:'soap',name:'Soap',qty:100,price:10,currentCostPrice:3,costPrice:3,division:'pharmacy',batches:[{id:'lot',qty:100,costPrice:3,createdAt:'2026-01-01T00:00:00.000Z'}]}])),
 price:v=>inventoryCommit(()=>{const p=clone(getStock());p[0].price=v;setStock(p);return true}),
 activity:(type,qty)=>inventoryCommit(()=>{const t={id:uid('tx'),type,domain:'retail',refKind:'product',productId:'soap',productName:'Soap',qty,unitPrice:10,amount:10*qty,costSnapshot:3,ts:Date.now(),division:'pharmacy',paymentFunding:type==='purchase_cash'?'external':'business'};if(!applyEffect(t,false,true))throw Error('Stock movement failed');tx.push(t);return true},'Sales Desk')
};'''
source=source.replace(marker,fixtures+marker)
def device(browser, version=None):
    ctx=browser.new_context()
    ctx.route(URL,lambda r:r.fulfill(content_type='text/html',body=version or source))
    p=ctx.new_page()
    p.goto(URL)
    p.wait_for_selector('#openSmartSyncSettings',state='attached',timeout=20000)
    assert p.evaluate("RoseachyStore.status().mode") == 'indexeddb'
    return p
def run(p, expr, arg=None):
    return p.evaluate('async arg=>{const s=RoseachySmartSync,f=fixture;'+expr+'}',arg)
def offer(p):
    return run(p,'await s.verifyRecovery(await f.backup());return s.offer()')
def trust(p,file):
    run(p,'const a=arg.payload.sender;await f.trust(a.deviceId,a.publicKey,true)',file)
def apply(p,file):
    return run(p,'return s.merge(await s.unprotect(arg))',file)
def updates(p):
    return run(p,'return s.updates()')
def reject(fn,reason):
    try: fn()
    except Exception as e:
        assert reason.lower() in str(e).lower(),str(e)
        return
    raise AssertionError('Expected rejection: '+reason)
def main(browser):
    a,b,c=[device(browser) for _ in range(3)]
    for p in (a,b):run(p,'await f.seed()')
    oa,ob=offer(a),offer(b)
    trust(a,ob);trust(b,oa)
    cp=run(a,"return s.createCheckpoint(await s.unprotect(arg),{approvedBy:'Tester',snapshotScope:true,sameBusiness:true})",ob)
    file=run(a,'return s.checkpointPackage(arg)',cp)
    approval="{sameBusiness:true,approvedBy:'Tester'}"
    run(a,'return s.acceptCheckpoint(arg,'+approval+')',cp)
    run(b,'return s.acceptCheckpoint((await s.unprotect(arg)).checkpoint,'+approval+')',file)
    print('PASS paired two independent IndexedDB profiles',flush=True)
    for p,kind,qty in [(a,'sale_cash',15),(b,'sale_cash',10),(b,'purchase_cash',30)]:
        assert run(p,'return f.activity(...arg)',[kind,qty])
    ua,ub=updates(a),updates(b)
    reject(lambda:apply(c,ua),'Connect and verify')
    import copy
    bad=copy.deepcopy(ua);bad['payload']['createdAt']='altered'
    reject(lambda:apply(b,bad),'authentication')
    print('PASS tampering and unauthorized sender',flush=True)
    apply(a,ub);apply(b,ua)
    for p in (a,b):
        assert run(p,'return f.stock()[0].qty')==105
        assert run(p,'return f.tx().length')==3
    balances=run(a,'return s.accountBalances()')
    assert balances==run(b,'return s.accountBalances()')
    assert balances=={'cash':250,'posCash':0,'posElectronic':0,'debt':0,'payable':0}
    assert apply(b,ua)['newEvents']==0
    print('PASS offline sales, receipt, ledger convergence and duplicate delivery',flush=True)
    for p in (a,b):
        ident=run(p,'return s.identity()');known=run(p,'return s.known()')
        p.reload();p.wait_for_selector('#openSmartSyncSettings',state='attached')
        assert run(p,'return s.identity().deviceId')==ident['deviceId']
        assert run(p,'return s.known()')==known,(known,run(p,'return s.backup().events.at(-1)'))
    print('PASS persistence across reload',flush=True)
    assert run(a,'return f.price(21)') and run(b,'return f.price(33)')
    rival=updates(a)
    plan=run(b,'return s.planUpdates(await s.unprotect(arg))',rival)
    conflicts=plan['conflicts'];assert any(x['type']=='product-definition' for x in conflicts),conflicts
    reject(lambda:apply(b,rival),'Resolve')
    run(b,"return s.merge(await s.unprotect(arg[0]),arg[1])",[rival,{x['key']:'incoming' for x in conflicts}])
    apply(a,updates(b))
    assert run(a,'return f.stock()[0].price')==run(b,'return f.stock()[0].price')
    print('PASS competing product prices and shared decision',flush=True)
    oc=offer(c);trust(a,oc);trust(b,oc);trust(c,oa);trust(c,ob)
    joined=run(a,"return s.join(await s.unprotect(arg),{sameBusiness:true,approvedBy:'Operator'})",oc)
    enrollment=run(a,'return s.checkpointPackage(arg)',joined)
    run(c,'return s.acceptCheckpoint((await s.unprotect(arg)).checkpoint,'+approval+')',enrollment)
    run(b,'return s.acceptJoin((await s.unprotect(arg)).checkpoint,'+approval+')',enrollment)
    apply(c,updates(b))
    assert run(c,'return f.stock()[0].qty')==105
    assert run(c,'return f.activity("sale_cash",2)')
    apply(b,updates(c));apply(a,updates(b))
    for p in (a,b,c):assert run(p,'return f.stock()[0].qty')==103
    print('PASS three devices forward signed events in both directions',flush=True)
    customer=run(a,"return f.credit.create({name:'Test account',startingBalance:50,startingConfirmed:true})")
    apply(b,updates(a))
    run(a,"return f.credit.purchase({customerId:arg,lines:[{productId:'soap',qty:1}]})",customer)
    run(b,"return f.credit.pay({customerId:arg,amount:20})",customer)
    ua,ub=updates(a),updates(b);apply(a,ub);apply(b,ua)
    price=run(a,'return f.stock()[0].price')
    for p in (a,b):
        assert run(p,'return f.credit.balance(arg)',customer)==50+price-20
    print('PASS concurrent credit purchase and repayment',flush=True)
    before=run(c,'return [f.stock(),f.tx(),await s.known()]')
    package=updates(a)
    # Abort the actual IndexedDB transaction after it starts writing.
    c.evaluate("""()=>{let attempts=0;const put=IDBObjectStore.prototype.put;IDBObjectStore.prototype.put=function(...args){
      const req=put.apply(this,args);if(this.transaction.objectStoreNames.contains('syncEventRecords')){
       if(++attempts===2)IDBObjectStore.prototype.put=put;this.transaction.abort();}return req;}}""")
    try:apply(c,package)
    except Exception:pass
    else:raise AssertionError('Expected aborted merge')
    assert before==run(c,'return [f.stock(),f.tx(),await s.known()]')
    c.reload();c.wait_for_selector('#openSmartSyncSettings',state='attached')
    assert before==run(c,'return [f.stock(),f.tx(),await s.known()]')
    apply(c,package)
    print('PASS transaction abort, reload, and retry',flush=True)
    for p in (a,b):assert run(p,'return f.activity("sale_cash",70)')
    ua,ub=updates(a),updates(b);apply(a,ub);apply(b,ua)
    for p in (a,b):
        assert run(p,'return f.stock()[0].syncBalance')==-38
        assert run(p,'return s.status().shortages[0].missing')==38
    print('PASS shortage retains both sales and flags 38 missing units',flush=True)
    ahead=run(a,"return f.price(37)");assert ahead
    assert run(a,"return f.price(38)")
    late=run(a,"const p=(await s.updates()).payload;return s.protect({...p,events:p.events.filter(e=>e.deviceId===s.identity().deviceId).slice(-1)})")
    reject(lambda:apply(c,late),'Missing')
    apply(c,updates(a));apply(b,updates(c));apply(a,updates(b))
    for p in (a,b,c):assert run(p,'return f.stock()[0].price')==38
    exchange=run(a,'return s.known()')
    for p in (b,c):assert run(p,'return s.known()')==exchange
    for sender,recipient in [(a,b),(b,c),(c,a)]:
        assert apply(recipient,updates(sender))['newEvents']==0
        assert run(recipient,'return s.status().lastConfirmed.digest')==exchange['digest']
    print('PASS out-of-order rejection, missing-event recovery and repeated cycles',flush=True)
    assert run(a,'return f.supplierInvoice()')
    apply(b,updates(a))
    assert run(b,'return f.supplierBalance()')==100
    run(b,'f.openPayment()')
    b.locator('#supplierPaymentAmount').fill('25')
    b.locator('#supplierPaymentSave').click()
    b.wait_for_function('fixture.supplierBalance()===75')
    apply(a,updates(b));apply(a,updates(b))
    assert run(a,'return f.supplierBalance()')==75
    assert run(a,"return f.tx().filter(t=>t.supplierPaymentId).length")==1
    print('PASS supplier credit purchase, payment form, outstanding balance and replay',flush=True)
    run(c,'s.open()')
    c.locator('#syncReceive').click()
    c.locator('#syncImportFile').set_input_files({'name':'update.json','mimeType':'application/json','buffer':json.dumps(updates(a)).encode()})
    c.locator('#syncConfirmMerge').click()
    c.wait_for_function("document.querySelector('#syncMessage').textContent.includes('Merge saved')")
    assert run(c,'return f.supplierBalance()')==75
    c.locator('[data-view="Sync"]').click()
    with c.expect_download():
        c.locator('#syncSend').click()
    print('PASS receive file picker, review, commit and send download',flush=True)

    for p in (a,b):
        run(p,"await f.credit.pay({customerId:arg,amount:3})",customer)
    payfile=updates(a)
    plan=run(b,'return s.planUpdates(await s.unprotect(arg))',payfile)
    similar=[c for c in plan['conflicts'] if c['type']=='similar-payments']
    assert len(similar)==1
    reject(lambda:apply(b,payfile),'Resolve')
    run(b,'return s.merge(await s.unprotect(arg[0]),arg[1])',[payfile,{similar[0]['key']:'separate'}])
    apply(a,updates(b))
    assert run(a,'return f.credit.balance(arg)',customer)==50+price-26
    print('PASS matching payments require an explicit receipt decision',flush=True)
    d=device(browser);run(d,'await f.seed()');nonempty=offer(d);trust(a,nonempty)
    reject(lambda:run(a,"return s.join(await s.unprotect(arg),{sameBusiness:true,approvedBy:'Tester'})",nonempty),'independent business records')
    assert run(d,'return f.stock()[0].qty')==100
    print('PASS enrollment stops for an independent nonempty third store',flush=True)

def pairing_ui(browser):
    devices=[device(browser) for _ in range(2)]
    def upload(p,selector,value):
        p.locator(selector).set_input_files({'name':'roseachy.json','mimeType':'application/json','buffer':json.dumps(value).encode()})
    def download(p,selector):
        with p.expect_download() as result:p.locator(selector).click()
        return json.loads(result.value.path().read_text())
    invitations=[]
    for p in devices:
        p.set_viewport_size({'width':390,'height':844})
        run(p,'s.open()')
        p.locator('[data-view="New Device"]').click()
        p.locator('#syncConnect summary').click()
        backup=download(p,'#syncRecoveryDownload')
        p.wait_for_function("document.querySelector('#syncMessage').textContent.includes('Select that file')")
        upload(p,'#syncRecoveryFile',backup)
        p.wait_for_function("document.querySelector('#syncRecoveryStatus').textContent.includes('verified ·')")
        invitations.append(download(p,'#syncExportOffer'))
    for p,other in zip(devices,reversed(invitations)):
        p.locator('#syncReceiveOffer').click()
        upload(p,'#syncImportFile',other)
        p.locator('#syncFingerprintChecked').check()
        p.locator('#syncTrustDevice').click()
        p.locator('#syncApproveInitial').wait_for()
        p.locator('#syncSameBusiness').check()
        p.locator('#syncApprover').fill('Operator')
        p.locator('#syncSnapshotScope').check()
    a,b=devices
    a.locator('#syncApproveInitial').click()
    a.wait_for_function("document.querySelector('#syncMessage').textContent.includes('Starting records approved')")
    connection=download(a,'#syncExportCheckpoint')
    b.locator('#syncOpenCheckpoint').click();upload(b,'#syncImportFile',connection)
    b.locator('#syncAcceptCheckpoint').wait_for()
    assert not b.locator('#syncSameBusiness').is_checked()
    b.locator('#syncSameBusiness').check()
    b.locator('#syncAcceptCheckpoint').click()
    b.wait_for_function("RoseachySmartSync.status().checkpointId!==null")
    assert run(a,'return s.status().checkpointId')==run(b,'return s.status().checkpointId')
    print('PASS mobile guided pairing with actual downloaded backups and invitations',flush=True)

def upgrade(browser):
    old=subprocess.check_output(['git','show','49f88a5:index.html'],cwd=SOURCE.parent,text=True)
    old=old.replace(marker,fixtures+marker)
    a,b=[device(browser,old) for _ in range(2)]
    for p in (a,b):run(p,'await f.seed()')
    oa,ob=offer(a),offer(b)
    trust(a,ob);trust(b,oa)
    cp=run(a,"return s.createCheckpoint(await s.unprotect(arg),{approvedBy:'Operator',sameBusiness:true,snapshotScope:true})",ob)
    for p in (a,b):run(p,"return s.acceptCheckpoint(arg,{approvedBy:'Operator',sameBusiness:true})",cp)
    assert run(a,'return f.activity("sale_cash",2)')
    for p in (a,b):
        ident=run(p,'return s.identity().deviceId')
        p.context.unroute(URL);p.context.route(URL,lambda r:r.fulfill(content_type='text/html',body=source))
        p.reload();p.wait_for_selector('#openSmartSyncSettings',state='attached')
        assert run(p,'return s.identity().deviceId')==ident
        assert run(p,'return s.status().checkpointId')==cp['id']
    apply(b,updates(a))
    assert run(b,'return [f.stock()[0].qty,f.tx().length]')==[98,1]
    print('PASS in-place upgrade from the original paired 2.17.2 databases',flush=True)
if __name__=='__main__':
    with sync_playwright() as pw:
        br=pw.chromium.launch(executable_path=shutil.which('chromium'),args=['--no-sandbox'])
        main(br)
        upgrade(br)
        pairing_ui(br)
