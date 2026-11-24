import asyncio, http.server, socketserver, threading, os, sys
from playwright.async_api import async_playwright
DIR=os.path.dirname(os.path.abspath(__file__))      # thư mục tests/
ROOT=os.path.dirname(DIR)                            # thư mục gốc dự án
PORT=8771; SEC='ABCD2345'
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
    room=454545; md=enc(room^0x5A5A5); mk=enc(room^0xA5A5A)
    async with async_playwright() as pw:
        br=await pw.chromium.launch(executable_path='/usr/bin/google-chrome',
            args=['--no-sandbox','--disable-dev-shm-usage','--mute-audio',
                  '--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream'])
        ctx=await br.new_context(reduced_motion='reduce', viewport={'width':1400,'height':1000},
                                 permissions=['microphone'])
        await ctx.add_init_script(path=os.path.join(DIR,'stub.js'))
        async def _loc(route):
            if '127.0.0.1' in route.request.url: await route.continue_()
            else: await route.abort()
        await ctx.route('**', _loc)
        pg=await ctx.new_page()
        errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
        await pg.goto(f'http://127.0.0.1:{PORT}/tests/harness.html')
        await pg.evaluate('(h)=>window.__mount("f-mc",h)','#mc/'+mk+'/'+SEC)
        await pg.evaluate('([r,t])=>{localStorage.setItem("rcv.doi."+r+".ten",JSON.stringify(t));localStorage.setItem("rcv.doi."+r+".nha",JSON.stringify(t))}',[room,'Minties'])
        await pg.evaluate('(h)=>window.__mount("f-a",h)','#doi/'+md)
        await pg.evaluate('(h)=>window.__mount("f-kg",h)','#duyet/'+mk+'/'+SEC)   # trang kiểm duyệt
        await pg.wait_for_timeout(1500)
        mc=pg.frame_locator('#f-mc'); du=pg.frame_locator('#f-kg'); ta=pg.frame_locator('#f-a')

        # ---- id riêng cho từng máy kiểm duyệt ----
        vid = await pg.evaluate('()=>{const d=document.getElementById("f-kg").contentWindow;return JSON.parse(d.localStorage.getItem("rcv.duyet.%d.vid")||"null")}'%room)
        ok('Kiểm duyệt: có id riêng (không còn dùng chung "kd")', bool(vid) and vid.startswith('kd') and vid!='kd', vid)

        # ---- kiểm duyệt vào phòng thoại + bật "cho khán giả nghe" để có mic ----
        await du.locator('#du-th-ra').check()
        await du.locator('#du-th-vao').click()
        await pg.wait_for_timeout(2500)
        ok('Kiểm duyệt: đã vào phòng thoại', 'Rời phòng thoại' in (await du.locator('#du-th-vao').inner_text()),
           await du.locator('#du-th-vao').inner_text())

        # ---- quản trò vào phòng thoại rồi thấy hàng kiểm duyệt có nút mic ----
        await mc.locator('#mc-th-vao').click()
        await pg.wait_for_timeout(9000)
        print('  [danh sách phòng thoại của quản trò]', await mc.locator('#mc-th-ds').inner_text(), flush=True)
        hang = mc.locator('#mc-th-ds > div').filter(has_text='Ban kiểm duyệt')
        ok('Quản trò: thấy hàng của máy kiểm duyệt', await hang.count()>=1, await hang.count())
        if await hang.count()==0:
            print('  [bỏ phần còn lại vì không thấy hàng kiểm duyệt]', flush=True)
            print('\nlỗi JS:', errs); await br.close()
            print('\nFAIL'); sys.exit(1)
        nut = hang.first.locator('button')
        ok('Quản trò: hàng kiểm duyệt CÓ nút mic', await nut.count()==1, await nut.count())
        ok('Quản trò: nút đang ở trạng thái mở', 'Đang mở' in (await nut.first.inner_text()), await nut.first.inner_text())

        # ---- tắt mic máy kiểm duyệt ----
        await nut.first.click()
        await pg.wait_for_timeout(1200)
        mt = await pg.evaluate('()=>{const d=document.getElementById("f-mc").contentWindow;return JSON.parse(d.localStorage.getItem("rcv.mc.%d.state")||"{}").micTat||[]}'%room)
        ok('Quản trò: id máy đó vào danh sách micTat', vid in mt, mt)
        ok('Quản trò: nút đổi thành "Đang tắt"', 'Đang tắt' in (await nut.first.inner_text()), await nut.first.inner_text())
        ok('Kiểm duyệt: nút mic báo bị quản trò tắt',
           'Quản trò đã tắt' in (await du.locator('#du-th-mic').inner_text()), await du.locator('#du-th-mic').inner_text())
        ok('Kiểm duyệt: không tự bật lại được', await du.locator('#du-th-mic').is_disabled())

        # ---- mở lại ----
        await nut.first.click()
        await pg.wait_for_timeout(1200)
        mt2 = await pg.evaluate('()=>{const d=document.getElementById("f-mc").contentWindow;return JSON.parse(d.localStorage.getItem("rcv.mc.%d.state")||"{}").micTat||[]}'%room)
        ok('Quản trò: mở lại thì id ra khỏi micTat', vid not in mt2, mt2)
        ok('Kiểm duyệt: nút mic dùng lại được', not await du.locator('#du-th-mic').is_disabled())

        # ---- mic của ĐỘI vẫn do micMo điều khiển như cũ ----
        hd = mc.locator('#mc-th-ds > div').filter(has_text='Minties').first
        nd = hd.locator('button').first
        t0 = await nd.inner_text()
        await nd.click(); await pg.wait_for_timeout(900)
        ok('Đội: nút mic vẫn đổi được trạng thái', (await nd.inner_text())!=t0, (t0, await nd.inner_text()))

        print('\nlỗi JS:', errs, flush=True)
        await br.close()
    print('\n'+('TẤT CẢ PASS' if not FAILS else 'FAIL: '+', '.join(FAILS)))
    sys.exit(1 if FAILS else 0)
asyncio.run(main())
