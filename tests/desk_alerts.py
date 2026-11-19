"""Exercise the workspace, Financial Desk, supplier and stock-expiry reminders in Chromium."""
import shutil
from playwright.sync_api import sync_playwright
from smart_sync import device, run
from sync_appearance import SOURCE

PAGE = SOURCE.replace('window.fixture={', '''window.fixture={
 setExpiry:(expiry,qty)=>inventoryCommit(()=>{
   const stock=clone(getStock());stock[0].expiryDate=expiry;stock[0].batches[0].expiryDate=expiry;
   if(qty===0){stock[0].qty=0;stock[0].batches=[]}
   setStock(stock);return true;
 }),''')
RING = '#deskMenuBtn .deskAlertRing'
FIN = '#financeMenuEntry .finDot'
MARKET = '#marketDebtDot'


def marker(page, selector, moving=True, pseudo=None):
    element=page.locator(selector)
    element.wait_for(state='visible',timeout=5000)
    # Sample two rendered frames of this specific repeating alert, independent of click feedback.
    values=element.evaluate("""(el,pseudo)=>{
      const style=()=>getComputedStyle(el,pseudo);
      const anim=el.getAnimations({subtree:true}).find(a=>a.animationName==='deskAlertPulse');
      if(!anim)return [style().animationName,style().opacity,style().display];
      const time=anim.currentTime,duration=anim.effect.getTiming().duration;
      anim.pause();anim.currentTime=0;const first=Number(style().opacity);
      anim.currentTime=duration/2;const middle=Number(style().opacity);
      anim.currentTime=time;anim.play();
      return [anim.effect.getTiming().iterations===Infinity,first,middle];
    }""",pseudo)
    if moving:
        assert values[0] is True and values[1]-values[2]>.5,(selector,values)
    else:
        assert values[0]=='none' and float(values[1])>0 and values[2]!='none',(selector,values)


def fill_pin(page, field):
    page.locator('[data-fin-pin="'+field+'"]').first.press_sequentially('8642')


def main(browser,width):
    page=device(browser,PAGE)
    page.set_viewport_size({'width':width,'height':844})
    menu=page.locator('#deskMenuBtn')
    assert not page.locator(RING).is_visible()
    page.locator('#openingCash').fill('200')
    page.locator('#finDayConfirm').click()
    page.wait_for_selector('#deskMenuBtn.finPulse')
    marker(page,RING)
    page.reload()
    page.wait_for_selector('#deskMenuBtn.finPulse')
    if width>600:
        run(page,"f.appearance({theme:'cobalt',colorMode:'dark'})")
    marker(page,RING)
    assert 'bank review pending' in menu.get_attribute('aria-label')
    menu.click()
    assert not page.locator(RING).is_visible()
    marker(page,FIN)
    page.locator('#financeMenuEntry').click()
    page.locator('#finAnchorInput').fill('100')
    fill_pin(page,'finSetupPassword');fill_pin(page,'finSetupPassword2')
    page.locator('#finSetupGo').click()
    page.locator('#finSetupDone').click()
    marker(page,'#finReviewStatus[data-pending]',pseudo='::after')
    page.locator('#finReviewQuick').click()
    page.locator('#finReviewActual').fill('100')
    page.locator('#finMarkReviewed').click()
    page.wait_for_function("document.querySelector('#finReviewStatus').textContent.includes('Reviewed')")
    assert not page.locator(RING).is_visible()
    # A new posted movement makes this review stale, including after locking the desk.
    page.locator('#finAdd').click()
    page.locator('#finEditAmount').fill('10')
    page.locator('#finEditReason').fill('Bank deposit')
    page.locator('#finEditSave').click()
    page.wait_for_selector('#deskMenuBtn.finPulse')
    menu.click();page.locator('[data-desk=sales]').click()
    marker(page,RING)
    page.reload();page.wait_for_selector('#deskMenuBtn.finPulse')
    # Both reminders share the workspace button and have separate menu entries.
    run(page,"await f.seed();await f.activity('sale_transfer',1);return f.supplierInvoice()")
    page.wait_for_selector('#deskMenuBtn.supplierDebtPulse')
    assert page.locator('#deskMenuBtn .supplierMark').is_visible()
    marker(page,RING);menu.click();marker(page,FIN);marker(page,MARKET)
    for patch in [{'reduceMotion':True},{'reduceMotion':False,'animation':'off'}]:
        run(page,'f.appearance(arg)',patch)
        marker(page,FIN,False);marker(page,MARKET,False)
    run(page,"f.appearance({reduceMotion:false,animation:'refined'})")
    page.emulate_media(reduced_motion='reduce')
    marker(page,FIN,False);marker(page,MARKET,False)
    menu.click();marker(page,RING,False)
    page.emulate_media(reduced_motion='no-preference')
    menu.click();page.locator('#financeMenuEntry').click()
    fill_pin(page,'finUnlockPass');page.locator('#finUnlockGo').click()
    pending='#finPendingConfirmations[data-pending]'
    marker(page,pending+' > summary',pseudo='::after')
    page.locator(pending+' > summary').click()
    page.locator(pending+' details > summary').first.click()
    page.locator(pending+' [data-reject]').first.click()
    page.wait_for_function("!document.querySelector('#finPendingConfirmations[data-pending]')")
    page.locator('#finReviewQuick').click();page.locator('#finReviewActual').fill('110')
    page.locator('#finMarkReviewed').click()
    page.wait_for_function("document.querySelector('#finReviewStatus').textContent.includes('Reviewed')")
    menu.click();assert not page.locator(FIN).is_visible();marker(page,MARKET)
    page.locator('[data-desk=sales]').click()
    page.wait_for_selector('#deskMenuBtn.supplierDebtPulse');marker(page,RING)
    run(page,'f.openPayment()')
    page.locator('#supplierPaymentAmount').fill('100')
    page.locator('#supplierPaymentSave').click()
    page.wait_for_function('fixture.supplierBalance()===0')
    page.wait_for_selector(RING,state='hidden')
    menu.click();assert not page.locator(MARKET).is_visible();menu.click()
    assert run(page,"return f.setExpiry('2020-01-01')")
    page.locator('#tabBtnStock').click()
    expiry='#stockExpiringLine.blink'
    marker(page,expiry,pseudo='::after')
    page.emulate_media(reduced_motion='reduce');marker(page,expiry,False,'::after')
    assert run(page,"return f.setExpiry('2020-01-01',0)"),page.locator('#toast').text_content()
    page.locator('#tabBtnTx').click();page.locator('#tabBtnStock').click()
    assert page.locator(expiry).count()==0
    print('PASS bank review, reload and re-review, concurrent supplier reminder, repayment, stock expiry and reduced motion')


if __name__=='__main__':
    with sync_playwright() as w:
        browser=w.chromium.launch(executable_path=shutil.which('chromium'),args=['--no-sandbox'])
        for width in (390,1280):
            main(browser,width)
