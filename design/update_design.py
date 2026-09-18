"""Update the user-relocated SVG designs in place; rerunnable without duplication."""
from pathlib import Path
import xml.etree.ElementTree as ET
from copy import deepcopy
from html import escape
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parent
NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)
def tag(s): return '{'+NS+'}'+s
palette = {
 '#101119':'#F6F5F2', '#1C1E2B':'#FFFFFF', '#9497AC':'#747486',
 '#F5F5FC':'#303345', '#A78BFA':'#8875AA', '#D1F47B':'#537866',
 '#171923':'#EFEDF3', '#535565':'#B5AFBF', '#151620':'#EEEDF0',
 '#302748':'#DDD5EA', '#302750':'#E6DEEF', '#302843':'#E6DEEF',
 '#302B45':'#E7E1EF', '#2B2644':'#EAE4F1', '#39304F':'#DDD4EA',
 '#C1B9D7':'#756784', '#BDB2CF':'#756784', '#C3B6D8':'#756784',
 '#272936':'#E6E3EA', '#303240':'#E6E3EA', '#606579':'#858290',
 '#191B27':'#EEEAF1', '#343A70':'#A7ABC8', '#405D62':'#9DB9B4',
 '#654153':'#C8AAB5', '#47416E':'#B4A7CD', '#8ED8C5':'#568A79',
 '#E7B48D':'#A57858', '#8FADEC':'#7489B5', '#090A10':'#EAE8ED',
}
def rect(parent,x,y,w,h,fill,r=16):
 return ET.SubElement(parent,tag('rect'),dict(x=str(x),y=str(y),width=str(w),height=str(h),rx=str(r),fill=fill))
def text(parent,x,y,s,size=14,color='#303345',weight=400,anchor=None):
 a=dict(x=str(x),y=str(y),fill=color,**{'font-size':str(size),'font-weight':str(weight),'font-family':'Microsoft YaHei, Noto Sans SC, sans-serif'})
 if anchor:a['text-anchor']=anchor
 n=ET.SubElement(parent,tag('text'),a);n.text=s;return n
def icon(parent,x,y,d,color='#8875AA',size=24):
 n=ET.SubElement(parent,tag('svg'),dict(x=str(x),y=str(y),width=str(size),height=str(size),viewBox='0 0 24 24'))
 ET.SubElement(n,tag('path'),dict(d=d,fill='none',stroke=color,**{'stroke-width':'1.6','stroke-linecap':'round','stroke-linejoin':'round'}));return n
def root(w=390,h=844):return ET.Element(tag('svg'),dict(width=str(w),height=str(h),viewBox=f'0 0 {w} {h}'))
def save(n,path):ET.ElementTree(n).write(path,encoding='utf-8',xml_declaration=True)

pages=[]
for path in sorted(ROOT.glob('0[1-7]-*.svg')):
 r=ET.parse(path).getroot()
 for n in r.iter():
  for attr in ('fill','stroke'):
   old=n.get(attr)
   if old in palette:n.set(attr,'#342C43' if n.tag==tag('text') and old=='#101119' else palette[old])
 for n in r.iter():
  if n.tag==tag('text') and n.get('fill')=='#342C43':n.set('fill','#FFFFFF')
  if n.tag==tag('rect') and n.get('fill')=='#8875AA':n.set('fill','#80699E')
 if path.name.startswith('01-') and r.find(".//*[@id='home-quick-actions']") is None:
  # Preserve all existing sections, shifting the content and bottom navigation together.
  r.set('height','928');r.set('viewBox','0 0 390 928')
  r[0].set('height','928')
  for n in list(r)[1:]:
   y=n.get('y')
   if y is not None and float(y)>=340:n.set('y',str(float(y)+84))
   elif n.tag==tag('path'):
    # Existing top-level price strike-throughs use absolute path coordinates.
    n.set('transform','translate(0 84)')
  g=ET.SubElement(r,tag('g'),id='home-quick-actions')
  actions=[('活动抽奖','M3 8h18v5H3Z M5 13v8h14v-8 M12 8v13 M12 8C2 8 6-2 12 8c6-10 10 0 0 0'),('下单流程','M6 3h12v18H6Z M9 8h6 M9 12h6 M9 16h4'),('客服中心','M4 14v-3a8 8 0 0 1 16 0v3 M4 12H2v7h4v-7Z M20 12h2v7h-4v-7Z M20 19c0 3-4 3-7 3'),('考核中心','M7 4h3V2h4v2h3v3H7Z M7 5H4v17h16V5h-3 M8 14l3 3 5-6')]
  for i,(label,d) in enumerate(actions):
   x=20+i*90
   item=ET.SubElement(g,tag('g'),{'aria-label':label})
   rect(item,x,343,80,68,'#FFFFFF',14)
   icon(item,x+28,352,d)
   text(item,x+40,397,label,12,anchor='middle')
 save(r,path);pages.append((path.stem,r))

r=root();rect(r,0,0,390,844,'#F6F5F2',0)
text(r,24,28,'9:41',13,weight=600);text(r,295,28,'▂ ▄ ▆  ▰',12)
text(r,337,77,'先逛逛',12,'#747486',anchor='middle')
rect(r,32,131,326,219,'#E6DEEF',28)
ET.SubElement(r,tag('circle'),dict(cx='295',cy='179',r='48',fill='#D8CEE7'))
ET.SubElement(r,tag('circle'),dict(cx='95',cy='305',r='29',fill='#D5E3DA'))
icon(r,158,170,'M7 6h10c4 0 6 14 2 14l-4-4H9l-4 4C1 20 3 6 7 6Z M8 9v5 M5.5 11.5h5 M16 10h.1 M18 13h.1','#8875AA',74)
text(r,195,279,'游伴 CLUB',26,weight=700,anchor='middle')
text(r,195,308,'一起开局，让热爱有伴',13,'#756784',anchor='middle')
text(r,32,405,'欢迎来到游伴',27,weight=700)
text(r,32,436,'登录后，与同好相遇，发现更多游戏乐趣',13,'#747486')
rect(r,32,478,326,52,'#80699E',16)
icon(r,111,493,'M20 10c0 5-5 8-10 6l-5 3 1-5C1 8 6 3 12 3c5 0 8 3 8 7Z M8 8h.1 M14 8h.1','#FFFFFF',22)
text(r,211,511,'微信一键登录',16,'#FFFFFF',600,anchor='middle')
rect(r,33,554,16,16,'#F6F5F2',4).set('stroke','#AAA3B5')
text(r,58,567,'我已阅读并同意',12,'#747486')
text(r,148,567,'《用户协议》',12,'#8875AA')
text(r,226,567,'与',12,'#747486')
text(r,244,567,'《隐私政策》',12,'#8875AA')
text(r,195,605,'首次登录将自动创建账号',11,'#747486',anchor='middle')
text(r,195,743,'游戏里的默契，从这里开始',12,'#747486',anchor='middle')
text(r,195,773,'登录遇到问题？ 联系客服',11,'#8875AA',anchor='middle')
rect(r,134,833,122,4,'#B5AFBF',2)
save(r,ROOT/'08-登录.svg');pages.append(('08-登录',r))

board=root(1744,2148);rect(board,0,0,1744,2148,'#EAE8ED',0)
text(board,32,53,'游伴 CLUB / 温和配色 · 移动端设计',28,weight=700)
text(board,32,83,'8 个页面 · 首页新增四个快捷入口 · 商品与用户信息均为示例',13,'#747486')
for i,(name,r) in enumerate(pages):
 x=32+(i%4)*430;y=148+(i//4)*1010
 text(board,x,y-20,name,16,weight=600)
 g=ET.SubElement(board,tag('g'),transform=f'translate({x} {y})')
 for n in r:g.append(deepcopy(n))
save(board,ROOT/'全部页面.svg')
html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>游伴 · 八页设计预览</title><style>body{margin:0;padding:32px;background:#EAE8ED;color:#303345;font-family:Microsoft YaHei,sans-serif}h1{font-size:26px}p{color:#747486;font-size:14px;line-height:1.8}.screens{display:flex;gap:28px;flex-wrap:wrap;align-items:flex-start}img{display:block;width:390px;max-width:100%;border:1px solid #DDD7E4;border-radius:24px}section{max-width:100%}h2{font-size:16px}</style><h1>游伴 CLUB · 温和配色</h1><p>8 页静态设计稿 / 暖白、灰紫与鼠尾草绿 / 登录页按微信小程序场景设计。<br>首页新增：活动抽奖、下单流程、客服中心、考核中心。商品、价格和账号均为示例。</p><div class="screens">'''
for name,r in pages:html+=f'<section><h2>{escape(name)}</h2><img src="{escape(name)}.svg?v=20260918" alt="{escape(name)}"></section>'
(ROOT/'index.html').write_text(html+'</div></html>',encoding='utf-8')
with ZipFile(ROOT/'Figma-SVG.zip','w',ZIP_DEFLATED) as z:
 for name,r in pages:z.write(ROOT/(name+'.svg'),name+'.svg')
 z.write(ROOT/'全部页面.svg','全部页面.svg')
print('Updated 8 individual SVGs, overview, HTML preview, and ZIP.')
