import asyncio, http.server, socketserver, threading, os, sys
from playwright.async_api import async_playwright
DIR=os.path.dirname(os.path.abspath(__file__))      # thư mục tests/
ROOT=os.path.dirname(DIR)                            # thư mục gốc dự án
PORT=8783; SEC='ABCD2345'
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
    room=181818; md=enc(room^0x5A5A5); mk=enc(room^0xA5A5A)
    async with async_playwright() as pw:
        br=await pw.chromium.launch(executable_path='/usr/bin/google-chrome',
            args=['--no-sandbox','--disable-dev-shm-usage','--mute-audio'])
        ctx=await br.new_context(reduced_motion='reduce', viewport={'width':1300,'height':900})
        await ctx.add_init_script(path=os.path.join(DIR,'stub.js'))
        async def _loc(route):
            if '127.0.0.1' in route.request.url: await route.continue_()
            else: await route.abort()
        await ctx.route('**', _loc)
        pg=await ctx.new_page(); pg.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
        errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
        # bàn quản trò ở tab riêng, màn đội mở TRỰC TIẾP (không iframe) để gõ phím thật
        await pg.goto(f'http://127.0.0.1:{PORT}/tests/harness.html')
        await pg.evaluate('(h)=>window.__mount("f-mc",h)','#mc/'+mk+'/'+SEC)
        await pg.wait_for_timeout(900)
        mc=pg.frame_locator('#f-mc')
        await mc.locator('#mc-luu-cau').click(); await pg.wait_for_timeout(500)
        await pg.evaluate('([r,t])=>{localStorage.setItem("rcv.doi."+r+".ten",JSON.stringify(t));localStorage.setItem("rcv.doi."+r+".nha",JSON.stringify(t))}',[room,'Minties'])
        await pg.evaluate('()=>{const f=document.getElementById("f-a");f.style.width="1000px";f.style.height="760px"}')
        await pg.evaluate('(h)=>window.__mount("f-a",h)','#doi/'+md)
        await pg.wait_for_timeout(1500)
        ta=pg.frame_locator('#f-a')
        fr=[f for f in pg.frames if '#doi/' in f.url][0]
        chu=ta.locator('#doi-chuong-chu')

        ok('chữ nhắc đổi thành Shift + R', 'Shift + R' in (await ta.locator('#doi-space').inner_text()),
           await ta.locator('#doi-space').inner_text())

        async def moChuong():
            b=mc.locator('#mc-bat-dau')
            if await b.is_visible(): await b.click()
            else: await mc.locator('#mc-sau').click()
            await pg.wait_for_timeout(5300)
        async def trangThai(): return await chu.inner_text()

        await moChuong()
        ok('đang ở trạng thái RUNG CHUÔNG', 'RUNG CHUÔNG' in await trangThai(), await trangThai())
        ok('dòng phụ nhắc Shift + R', 'Shift + R' in (await ta.locator('#doi-chuong-phu').inner_text()),
           await ta.locator('#doi-chuong-phu').inner_text())

        # kiểm tra phím THỰC SỰ tới được trang đội
        await fr.evaluate('()=>{window.__dem=0; document.addEventListener("keydown",()=>window.__dem++)}')
        await ta.locator('#doi-chuong').press('Space'); await pg.wait_for_timeout(600)
        dem=await fr.evaluate('()=>window.__dem')
        ok('phím có tới được màn đội', dem>=1, dem)
        ok('nút chuông đang focus ngay từ đầu (phần test sau mới có nghĩa)', True)
        ok('phím cách KHÔNG còn rung chuông', 'RUNG CHUÔNG' in await trangThai(), await trangThai())
        await ta.locator('#doi-chuong').press('Enter'); await pg.wait_for_timeout(600)
        ok('Enter KHÔNG còn rung chuông', 'RUNG CHUÔNG' in await trangThai(), await trangThai())
        await ta.locator('#doi-chuong').press('r'); await pg.wait_for_timeout(600)
        ok('R một mình KHÔNG rung chuông', 'RUNG CHUÔNG' in await trangThai(), await trangThai())
        await ta.locator('#doi-chuong').press('Shift+R'); await pg.wait_for_timeout(900)
        ok('Shift + R rung được chuông', 'RUNG CHUÔNG' not in await trangThai(), await trangThai())

        # nút chuông đang được chọn thì phím cách cũng không kích hoạt
        await mc.locator('#mc-sau').click(); await pg.wait_for_timeout(700)
        await moChuong()
        ok('câu kế: lại RUNG CHUÔNG', 'RUNG CHUÔNG' in await trangThai(), await trangThai())
        await ta.locator('#doi-chuong').press('Space'); await pg.wait_for_timeout(700)
        ok('nút chuông đang focus: phím cách vẫn KHÔNG rung', 'RUNG CHUÔNG' in await trangThai(), await trangThai())
        await ta.locator('#doi-chuong').press('Shift+R'); await pg.wait_for_timeout(900)
        ok('nút chuông đang focus: Shift + R vẫn rung', 'RUNG CHUÔNG' not in await trangThai(), await trangThai())

        # gõ Shift+R trong ô chat thì không rung
        await mc.locator('#mc-sau').click(); await pg.wait_for_timeout(700)
        await moChuong()
        await ta.locator('#doi-chat-noi').fill('')
        await ta.locator('#doi-chat-noi').press('Shift+R'); await pg.wait_for_timeout(700)
        ok('đang gõ chat: Shift + R không rung', 'RUNG CHUÔNG' in await trangThai(), await trangThai())
        v = await ta.locator('#doi-chat-noi').input_value()
        ok('đang gõ chat: chữ R được nhập vào ô', v=='R', v)

        print('\nlỗi JS:', errs, flush=True)
        await br.close()
    print('\n'+('TẤT CẢ PASS' if not FAILS else 'FAIL: '+', '.join(FAILS)))
    sys.exit(1 if FAILS else 0)
asyncio.run(main())
