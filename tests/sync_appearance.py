"""Check rendered theme colors, responsive geometry, and the two business accordions."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json
import shutil
from smart_sync import source, device, run, offer

GEOMETRY = ['spacingLevel', 'fieldSizeLevel', 'sectionSizeLevel', 'verticalRhythmLevel',
            'verticalCompactnessLevel', 'roundnessLevel', 'borderWeightLevel', 'shadowLevel']
SOURCE = source.replace('window.fixture={', '''window.fixture={
 themes:Object.keys(RS_THEMES),
 appearance:patch=>applyAppearanceSettings({...getAppearanceSettings(),...patch}),
 pendingPurchase:()=>inventoryCommit(()=>{
   const t={id:uid('tx'),type:'purchase_credit',domain:'retail',refKind:'product',
    productId:'soap',productName:'Soap',qty:4,unitPrice:10,amount:40,ts:nowIso()};
   if(!applyEffect(t,false,true))throw Error('Purchase failed');tx.push(t);return true
 },'Market Desk'),''')

def main(browser):
    p=device(browser,SOURCE)
    errors=[]
    p.on('pageerror',lambda e:errors.append(str(e)))
    p.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
    cover=Path(__file__).resolve().parents[1]/'screenshots'
    cover.mkdir(exist_ok=True)
    run(p,'s.open()')
    assert p.locator('#syncOverlay').get_by_role('tab').all_text_contents()==['Sync','New Device','History']
    for theme in run(p,'return f.themes'):
        for mode in ['light','dark']:
            run(p,'f.appearance(arg)',{'theme':theme,'colorMode':mode})
            for selector in ['.syncHeader','#syncSend']:
                p.wait_for_function("""selector=>{const el=document.querySelector(selector);
                  const probe=document.createElement('i');probe.style.color='var(--accent-primary)';
                  el.append(probe);const expected=getComputedStyle(probe).color;probe.remove();
                  const style=getComputedStyle(el);return style.backgroundColor===expected && style.backgroundImage==='none'
                }""",arg=selector,timeout=3000)
    sizes=[]
    for level in [0,50,100]:
        run(p,'f.appearance(arg)',dict.fromkeys(GEOMETRY,level))
        sizes.append(p.locator('.syncPanel').evaluate("e=>[getComputedStyle(e).borderRadius,getComputedStyle(e).borderWidth,getComputedStyle(e).boxShadow]"))
        for width,height in [(320,740),(390,844),(768,1024),(1280,880)]:
            p.set_viewport_size({'width':width,'height':height})
            for name in ['New Device','History','Sync']:
                p.get_by_role('tab',name=name,exact=True).click()
                assert p.locator('.syncPanel').evaluate("el=>el.scrollWidth<=el.clientWidth+1"),(level,width,name)
    assert all(len({row[i] for row in sizes})==3 for i in range(3)),sizes
    run(p,'f.appearance(arg)',{**dict.fromkeys(GEOMETRY,50),'theme':'ember','colorMode':'light'})
    for width,height,name,file in [(390,844,'Sync','mobile-sync'),(768,1024,'New Device','tablet-new-device')]:
        p.set_viewport_size({'width':width,'height':height})
        p.get_by_role('tab',name=name,exact=True).click()
        p.locator('.syncPanel').screenshot(path=cover/(file+'.png'),animations='disabled')
    p.get_by_role('tab',name='New Device').press('ArrowRight')
    assert p.get_by_role('tab',name='History').get_attribute('aria-selected')=='true'
    assert p.locator('#syncLog').inner_text()=='No sync activity yet.'
    run(p,'await f.seed();return f.activity("sale_cash",10)')
    p.get_by_role('tab',name='Sync',exact=True).click()
    p.locator('#syncAdvances summary').click()
    p.locator('#syncAdvanceReason').fill('Market supplies')
    p.locator('#syncAdvanceAmount').fill('30')
    p.locator('#syncAdvances summary').click();p.locator('#syncAdvances summary').click()
    assert p.locator('#syncAdvanceAmount').input_value()=='30'
    p.locator('#syncAdvanceCreate').click()
    p.wait_for_function("RoseachySmartSync.advanceBalance(document.querySelector('#syncAdvanceSelect').value)===30")
    p.locator('#syncAdvanceReturn').fill('10');p.locator('#syncAdvanceReturnSave').click()
    p.wait_for_function("RoseachySmartSync.advanceBalance(document.querySelector('#syncAdvanceSelect').value)===20")
    assert run(p,"return f.tx().filter(t=>t.type==='market_advance_return').length")==1
    p.locator('#syncStockReceipts summary').click();p.locator('#syncReceiveNow').uncheck()
    assert run(p,'return f.pendingPurchase()')
    assert run(p,'return f.stock()[0].qty')==90
    p.get_by_role('tab',name='Sync',exact=True).click()
    p.locator('[data-sync-receive]').click()
    p.wait_for_function("fixture.stock()[0].qty===94 && !document.querySelector('[data-sync-receive]')")
    receipt=run(p,"return f.tx().find(t=>t.receiptSourceId).receiptSourceId")
    assert run(p,'return s.receive(arg)',receipt) is False
    other=device(browser);invitation=offer(other)
    with p.expect_file_chooser() as picker:p.locator('#syncReceive').click()
    picker.value.set_files({'name':'invite.json','mimeType':'application/json','buffer':json.dumps(invitation).encode()})
    p.wait_for_function("document.querySelector('#syncMessage').textContent.includes('Choose an update')")
    p.get_by_role('tab',name='History').click()
    assert 'Needs attention' in p.locator('#syncLog').inner_text()
    p.reload();p.wait_for_selector('#openSmartSyncSettings',state='attached');run(p,'s.open()')
    p.get_by_role('tab',name='History').click()
    assert 'Needs attention' in p.locator('#syncLog').inner_text()
    p.set_viewport_size({'width':1280,'height':880})
    run(p,"f.appearance({theme:'cobalt',colorMode:'light'})")
    p.locator('.syncPanel').screenshot(path=cover/'desktop-history.png',animations='disabled')
    assert not errors,errors
    print('PASS palette, geometry, viewports, keyboard, cash advance and return, physical receipt and replay, file purpose, history persistence, console')
if __name__=='__main__':
    with sync_playwright() as w:
        main(w.chromium.launch(executable_path=shutil.which('chromium'),args=['--no-sandbox']))
