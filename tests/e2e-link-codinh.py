import asyncio, http.server, socketserver, threading, os, sys
from playwright.async_api import async_playwright
DIR=os.path.dirname(os.path.abspath(__file__))      # thư mục tests/
ROOT=os.path.dirname(DIR)                            # thư mục gốc dự án
PORT=8762; SEC='ABCD2345'
class S(socketserver.ThreadingMixIn, http.server.HTTPServer): daemon_threads=True
class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self,*a,**k): super().__init__(*a,directory=ROOT,**k)
    def log_message(self,*a): pass
threading.Thread(target=lambda: S(('127.0.0.1',PORT),H).serve_forever(),daemon=True).start()
FAILS=[]
def ok(n,c,extra=''):
    print(('PASS  ' if c else 'FAIL  ')+n+(('   << '+str(extra)) if (not c and extra!='') else ''))
    if not c: FAILS.append(n)
AL='0123456789ABCDEFGHJKMNPQRSTVWXYZ'
def enc(n):
    s=''
    for _ in range(4): s=AL[n&31]+s; n>>=5
    return s

async def main():
    room=727272; mk=enc(room^0xA5A5A)
    async with async_playwright() as pw:
        br=await pw.chromium.launch(executable_path='/usr/bin/google-chrome',
            args=['--no-sandbox','--disable-dev-shm-usage','--mute-audio'])
        ctx=await br.new_context(reduced_motion='reduce', viewport={'width':1280,'height':900})
        await ctx.add_init_script(path=os.path.join(DIR,'stub.js'))
        pg=await ctx.new_page()
        errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
        await pg.goto(f'http://127.0.0.1:{PORT}/tests/harness.html')

        # 1) CHƯA có phòng nào: link cố định phải báo "chưa thấy phòng", không treo
        await pg.evaluate('(h)=>window.__mount("f-kg",h)','#man')
        await pg.wait_for_timeout(600)
        kg=pg.frame_locator('#f-kg')
        ok('Link cố định: hiện dòng đang tìm', 'tìm phòng' in (await kg.locator('#home-tim').inner_text()))
        ok('Link cố định: vẫn ở trang chủ, còn ô nhập mã', await kg.locator('#in-ma-kg').is_visible())

        # 2) Mở bàn quản trò -> link cố định phải tự vào phòng đó
        await pg.evaluate('(h)=>window.__mount("f-mc",h)','#mc/'+mk+'/'+SEC)
        await pg.wait_for_timeout(900)
        await pg.evaluate('(h)=>window.__mount("f-a",h)','#man')   # mở link cố định lần nữa
        await pg.wait_for_timeout(2500)
        href = await pg.evaluate('()=>document.getElementById("f-a").contentWindow.location.hash')
        ok('Link cố định: tự chuyển sang #man/<mã phòng>', href=='#man/'+mk, href)
        ta=pg.frame_locator('#f-a')
        ok('Link cố định: đã vào màn khán giả', await ta.locator('#v-kg').is_visible())

        # 3) Quản trò tắt ô -> tin giữ lại bị xoá
        await pg.frame_locator('#f-mc').locator('#mc-link-chung').uncheck()
        await pg.wait_for_timeout(500)
        tin = await pg.evaluate('()=>window.__rcvBroker.retained["rcvang/dangchoi"]')
        ok('MC tắt ô: tin dangchoi đã bị xoá', (tin or '')=='', repr(tin))

        print('\nlỗi JS:', errs)
        await br.close()
    print('\n'+('TẤT CẢ PASS' if not FAILS else 'FAIL: '+', '.join(FAILS)))
    sys.exit(1 if FAILS else 0)
asyncio.run(main())
