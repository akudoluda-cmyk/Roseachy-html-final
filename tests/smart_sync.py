"""Run with Python Playwright and Chromium. All records live in isolated browser contexts."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import shutil

SOURCE = Path(__file__).resolve().parents[1] / 'index.html'
URL = 'http://localhost:9831/'
source = SOURCE.read_text()
# Expose fixture builders inside the closure only in the test response.
marker = 'window.RoseachySmartSync=api;'
assert source.count(marker) == 1
source = source.replace(marker, '''window.fixture={
 credit:CreditAccounts,backup:roseachySafeBackup,trust:SyncPrivacy.trust,stock:getStock,tx:()=>tx,
 seed:()=>RS.atomic(()=>setStock([{id:'soap',name:'Soap',qty:100,price:10,currentCostPrice:3,costPrice:3,division:'pharmacy',batches:[{id:'lot',qty:100,costPrice:3,createdAt:'2026-01-01T00:00:00.000Z'}]}])),
 price:v=>inventoryCommit(()=>{const p=clone(getStock());p[0].price=v;setStock(p);return true}),
 activity:(type,qty)=>inventoryCommit(()=>{const t={id:uid('tx'),type,domain:'retail',refKind:'product',productId:'soap',productName:'Soap',qty,unitPrice:10,amount:10*qty,costSnapshot:3,ts:Date.now(),division:'pharmacy',paymentFunding:type==='purchase_cash'?'external':'business'};if(!applyEffect(t,false,true))throw Error('Stock movement failed');tx.push(t);return true},'Sales Desk')
};'''+marker)
def device(browser):
    ctx=browser.new_context()
    ctx.route(URL,lambda r:r.fulfill(content_type='text/html',body=source))
    p=ctx.new_page()
    p.goto(URL)
    p.wait_for_selector('#openSmartSyncSettings',state='attached',timeout=20000)
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
    assert run(a,'return s.accountBalances()')==run(b,'return s.accountBalances()')
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
    print('PASS out-of-order rejection, missing-event recovery and repeated cycles',flush=True)
if __name__=='__main__':
    with sync_playwright() as pw:
        br=pw.chromium.launch(executable_path=shutil.which('chromium'),args=['--no-sandbox'])
        main(br)
