"""Check rounded text controls, button motion and the remaining full-backup action."""
import shutil
from playwright.sync_api import sync_playwright
from smart_sync import device, run
from sync_appearance import SOURCE


def text_inset(button, child=None):
    return button.evaluate("""(button, child) => {
      const range=document.createRange();
      range.selectNodeContents(child ? button.querySelector(child) : button);
      const edge=button.getBoundingClientRect();
      return Math.min(...Array.from(range.getClientRects(),r=>Math.min(r.left-edge.left,edge.right-r.right)));
    }""", child)


def open_desk(page, desk):
    page.locator('#deskMenuBtn').click()
    page.locator('#deskMenu [data-desk="'+desk+'"]').click()


def layout(page):
    assert page.locator('#rsPortableSafety button').count()==0
    banner=page.locator('#rsPortableSafety')
    assert banner.is_hidden() and banner.bounding_box() is None
    assert banner.text_content()==''
    for width in [320,390,768,1280]:
        page.set_viewport_size({'width':width,'height':844})
        page.locator('#tabBtnTx').click()
        assert text_inset(page.locator('#moveCashBtn'))>=12
        page.locator('#tabBtnStock').click()
        adjustment=page.locator('[data-target=stockAdjBody]')
        if adjustment.get_attribute('aria-expanded')!='true':
            adjustment.click()
        assert text_inset(page.locator('#adjApplyBtn'))>=12
        nav=page.locator('#tabBtnAnalytics')
        nav.click()
        nav.evaluate("el=>Promise.all(el.getAnimations({subtree:true}).map(a=>a.finished.catch(()=>{})))")
        assert text_inset(nav,'.navLabel')>=6
        open_desk(page,'settings')
        comfortable=page.get_by_role('button',name='Comfortable',exact=True)
        assert text_inset(comfortable)>=8
        open_desk(page,'sales')


def motion(page):
    button=page.locator('[data-target=daySetupBody]')
    button.focus()
    # Inspect the actual animations started by the delegated input handlers.
    probe="""button=>{
      const press=button.getAnimations().find(a=>'scale' in a.effect.getKeyframes()[0]);
      const sheen=button.querySelector('.rsButtonSheen');
      if(press){
        press.pause();
        press.currentTime=press.effect.getTiming().duration*.24;
        const [x,y]=getComputedStyle(button).scale.split(' ').map(Number);
        if(!(x>1&&y<1))throw Error('No rendered squash');
        press.finish();
      }
      const sweep=sheen?.getAnimations()[0];
      if(sweep){
        sweep.pause();sweep.currentTime=sweep.effect.getTiming().duration*.35;
        if(Number(getComputedStyle(sheen).opacity)<=0||getComputedStyle(sheen).backgroundImage==='none')throw Error('No rendered glint');
        sweep.finish();
      }
      return [!!sweep,!!press];
    }"""
    for patch,expected in [
        ({},[True,True]),({'pressResponse':False},[True,False]),
        ({'glint':False},[False,True]),({'reduceMotion':True},[False,False]),
        ({'animation':'off'},[False,False]),({'animation':'minimal'},[False,True])
    ]:
        run(page,'f.appearance(arg)',{'glint':True,'pressResponse':True,'animation':'refined','reduceMotion':False,**patch})
        button.focus()
        page.keyboard.down('Space')
        assert button.evaluate(probe)==expected,patch
        page.keyboard.up('Space')
        page.wait_for_function("!document.querySelector('.rsButtonSheen')")
    run(page,"f.appearance({animation:'refined',glint:true,pressResponse:true})")
    for reduced,expected in [('no-preference',[True,True]),('reduce',[False,False])]:
        page.emulate_media(reduced_motion=reduced)
        button.hover()
        page.mouse.down()
        assert button.evaluate(probe)==expected,reduced
        page.mouse.up()
    page.emulate_media(reduced_motion='no-preference')


def backup(page):
    open_desk(page,'settings')
    page.locator('#roseachyDataSafety summary').click()
    with page.expect_download() as download:
        page.locator('#safetyExportBtn').click()
    file=download.value
    assert 'Full-Backup' in file.suggested_filename
    page.locator('#safetyBackupCheckFile').set_input_files({
        'name':file.suggested_filename,'mimeType':'application/json','buffer':file.path().read_bytes()
    })
    page.wait_for_function("document.querySelector('#safetyFileStatus').textContent.includes('Backup structure valid')")


if __name__=='__main__':
    with sync_playwright() as w:
        browser=w.chromium.launch(executable_path=shutil.which('chromium'),args=['--no-sandbox'])
        page=device(browser,SOURCE)
        layout(page)
        page.locator('#tabBtnTx').click()
        motion(page)
        backup(page)
        print('PASS header, responsive text bounds, pointer and keyboard feedback, motion preferences, verified backup download')
