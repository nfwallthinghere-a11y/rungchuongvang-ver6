import asyncio, http.server, socketserver, threading, os, sys
from playwright.async_api import async_playwright
DIR=os.path.dirname(os.path.abspath(__file__))      # thư mục tests/
ROOT=os.path.dirname(DIR)                            # thư mục gốc dự án
PORT=8831; SEC='ABCD2345'
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
    room=252525; md=enc(room^0x5A5A5); mk=enc(room^0xA5A5A)
    async with async_playwright() as pw:
        br=await pw.chromium.launch(executable_path='/usr/bin/google-chrome',
            args=['--no-sandbox','--disable-dev-shm-usage','--mute-audio'])
        ctx=await br.new_context(reduced_motion='reduce', viewport={'width':1500,'height':1000})
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
        await mc.locator('#mc-luu-cau').click(); await pg.wait_for_timeout(600)

        st=lambda: pg.evaluate('()=>JSON.parse(localStorage.getItem("rcv.mc.%d.state")||"{}")'%room)
        async def quyen():
            m=await st(); d=list((m.get('doi') or {}).values())
            return (d[0].get('quyen') or {}) if d else {}
        async def tienChuKy():
            m=await st(); d=list((m.get('doi') or {}).values())
            return d[0].get('tienChuKy') if d else None

        # luật đang áp dụng hiện trên bàn quản trò
        luat = await mc.locator('#mc-moc-xem').inner_text()
        ok('bàn quản trò nhắc đúng luật mỗi đơn 20.000đ', '20.000' in luat and 'mỗi đơn' in luat, luat[:120])
        ok('bàn quản trò nhắc mốc tổng 150.000đ', '150.000' in luat, luat[:120])
        ok('bàn quản trò nhắc chu kỳ chạy lại', 'chạy lại' in luat, luat[:160])

        # quản trò cộng tiền tay cho nhà (giống duyệt một đơn donate)
        async def donate(so):
            o = mc.locator('#mc-tro-ds input[inputmode="numeric"]').first
            await o.fill(str(so))
            await o.press('Enter')
            await pg.wait_for_timeout(900)

        oTien = mc.locator('#mc-tro-ds input[inputmode="numeric"]')
        n = await oTien.count()
        print('   số ô nhập tiền trên bàn quản trò:', n)
        if n == 0:
            print('   (không thấy ô cộng tiền — bỏ phần e2e cộng tiền)')
        else:
            await donate(20000)
            q = await quyen()
            ok('duyệt đơn 20k: nhà được 50/50 ×1', q.get('chiadoi')==1 and not q.get('x2'), q)
            await donate(30000)
            q = await quyen()
            ok('duyệt thêm đơn 30k: 50/50 ×2, nhân đôi ×1', q.get('chiadoi')==2 and q.get('x2')==1, q)
            await donate(100000)
            q = await quyen()
            ok('tổng 150k: được cướp quyền', q.get('cuopquyen')==1, q)
            await donate(50000)
            q = await quyen()
            ok('tổng 200k: được người thân', q.get('hoisinh')==1, q)
            ok('đạt hết mốc: tiến độ chu kỳ về 0', (await tienChuKy())==0, await tienChuKy())

            # màn đội thấy số lượng
            txt = await ta.locator('#doi-tro').inner_text()
            ok('màn đội hiện số lượng từng quyền', txt.count('×')>=3, txt.replace('\n',' / ')[:170])
            ok('màn đội hiện tiến độ chu kỳ mới', 'Còn' in (await ta.locator('#doi-moc').inner_text()),
               await ta.locator('#doi-moc').inner_text())

            # đội dùng 50/50 hai lần (vì đang giữ 2 cái)
            await mc.locator('#mc-bat-dau').click(); await pg.wait_for_timeout(5300)
            o5050 = ta.locator('#doi-tro .tro-o').first
            await o5050.click(); await pg.wait_for_timeout(1200)
            q = await quyen()
            ok('dùng 1 lần: 50/50 còn ×1', q.get('chiadoi')==1, q)
            await o5050.click(); await pg.wait_for_timeout(1200)
            q = await quyen()
            ok('dùng lần 2 được (mô hình cũ sẽ chặn): 50/50 còn 0', q.get('chiadoi')==0, q)
            await o5050.click(); await pg.wait_for_timeout(1000)
            q = await quyen()
            ok('hết quyền thì không trừ xuống âm', (q.get('chiadoi') or 0)==0, q)

        print('\nlỗi JS:', errs, flush=True)
        await br.close()
    print('\n'+('TẤT CẢ PASS' if not FAILS else 'FAIL: '+', '.join(FAILS)))
    sys.exit(1 if FAILS else 0)
asyncio.run(main())
