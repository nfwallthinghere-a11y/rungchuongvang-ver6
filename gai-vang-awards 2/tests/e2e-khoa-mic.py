import asyncio, http.server, socketserver, threading, os, sys
from playwright.async_api import async_playwright
DIR=os.path.dirname(os.path.abspath(__file__))      # thư mục tests/
ROOT=os.path.dirname(DIR)                            # thư mục gốc dự án
PORT=8821; SEC='ABCD2345'
class S(socketserver.ThreadingMixIn, http.server.HTTPServer): daemon_threads=True
class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self,*a,**k): super().__init__(*a,directory=ROOT,**k)
    def log_message(self,*a): pass
threading.Thread(target=lambda: S(('127.0.0.1',PORT),H).serve_forever(),daemon=True).start()
FAILS=[]
def ok(n,c,extra=''):
    print(('PASS  ' if c else 'FAIL  ')+n+(('   << '+str(extra)) if (not c and extra!='') else ''),flush=True)
    if not c: FAILS.append(n)
AL='0123456789ABCDEFGHJKMNPQRSTVWXYZ'
def enc(n):
    s=''
    for _ in range(4): s=AL[n&31]+s; n>>=5
    return s
async def main():
    room=131313; md=enc(room^0x5A5A5); mk=enc(room^0xA5A5A)
    async with async_playwright() as pw:
        br=await pw.chromium.launch(executable_path='/usr/bin/google-chrome',
            args=['--no-sandbox','--disable-dev-shm-usage','--mute-audio',
                  '--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream'])
        ctx=await br.new_context(viewport={'width':1500,'height':1000}, permissions=['microphone'])
        await ctx.add_init_script(path=os.path.join(DIR,'stub.js'))
        async def _loc(r):
            if '127.0.0.1' in r.request.url: await r.continue_()
            else: await r.abort()
        await ctx.route('**', _loc)
        pg=await ctx.new_page(); pg.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
        errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(f'http://127.0.0.1:{PORT}/tests/harness.html')
        await pg.evaluate('(h)=>window.__mount("f-mc",h)','#mc/'+mk+'/'+SEC)
        await pg.evaluate('([r,t])=>{localStorage.setItem("rcv.doi."+r+".ten",JSON.stringify(t));localStorage.setItem("rcv.doi."+r+".nha",JSON.stringify(t))}',[room,'Minties'])
        await pg.evaluate('(h)=>window.__mount("f-a",h)','#doi/'+md)
        await pg.wait_for_timeout(1500)
        mc=pg.frame_locator('#f-mc'); ta=pg.frame_locator('#f-a')
        await mc.locator('#mc-luu-cau').click(); await pg.wait_for_timeout(500)
        # quản trò vào phòng thoại
        await mc.locator('#mc-th-vao').click(); await pg.wait_for_timeout(3000)
        # đội vào phòng thoại + bật mic
        await ta.locator('#doi-th-nut').click(); await pg.wait_for_timeout(3500)
        print('   nút mic của đội:', await ta.locator('#doi-th-nut').inner_text())

        # id riêng của đội để lọc đúng gói tiếng CỦA ĐỘI
        doiId = await pg.evaluate('()=>JSON.parse(localStorage.getItem("rcv.doi.%d.id.minties")||"null")'%room)
        print('   id của đội:', doiId)
        assert doiId, 'không lấy được id đội'

        async def demGoi(giay, ai=None):
            ai = ai or doiId
            await pg.evaluate('()=>{window.__rcvBroker.log.length=0}')
            await pg.wait_for_timeout(int(giay*1000))
            return await pg.evaluate('(ai)=>window.__rcvBroker.log.filter(m=>m.topic.endsWith("/am/"+ai)).length', ai)

        # đội phải tự bật mic lên trước đã
        if 'bấm để nói' in (await ta.locator('#doi-th-nut').inner_text()):
            await ta.locator('#doi-th-nut').click(); await pg.wait_for_timeout(1200)
        print('   nút mic của đội sau khi bật:', await ta.locator('#doi-th-nut').inner_text())

        truoc = await demGoi(3)
        ok('đội đang thật sự gửi tiếng (test có nghĩa)', truoc>0, truoc)

        # ---- quản trò KHOÁ mic đội ----
        hang = mc.locator('#mc-th-ds > div').filter(has_text='Minties').first
        nut = hang.locator('button').first
        print('   nút ở hàng đội trên bàn quản trò:', await nut.inner_text())
        await nut.click(); await pg.wait_for_timeout(1500)
        print('   sau khi bấm:', await nut.inner_text())
        print('   nút mic của đội:', await ta.locator('#doi-th-nut').inner_text())
        ok('đội thấy chữ "chờ quản trò mở mic"',
           'Chờ quản trò' in (await ta.locator('#doi-th-nut').inner_text()),
           await ta.locator('#doi-th-nut').inner_text())

        sau = await demGoi(3)
        ok('ĐỘI NGỪNG GỬI TIẾNG sau khi bị khoá', sau==0, 'vẫn gửi %d gói trong 3 giây'%sau)

        # ---- mở lại ----
        await nut.click(); await pg.wait_for_timeout(1500)
        lai = await demGoi(3)
        ok('mở lại thì đội gửi tiếng được', lai>0, lai)

        print('\nlỗi JS:', errs, flush=True)
        await br.close()
    print('\n'+('TẤT CẢ PASS' if not FAILS else 'FAIL: '+', '.join(FAILS)))
    sys.exit(1 if FAILS else 0)
asyncio.run(main())
