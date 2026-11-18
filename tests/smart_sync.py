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
 backup:roseachySafeBackup,trust:SyncPrivacy.trust,stock:getStock,tx:()=>tx,
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
if __name__=='__main__':
    with sync_playwright() as pw:
        br=pw.chromium.launch(executable_path=shutil.which('chromium'),args=['--no-sandbox'])
        main(br)
