# -*- coding: utf-8 -*-
"""V2: 重构手机客服知识库 - 修正参数、版本拆分、专属FAQ、业务数据、意图表、评测集"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import os, random

BASE = r"C:\Users\Administrator\Doubao\chats\2026-09-03\new-chat-5"
KB = os.path.join(BASE, "kb-docs")
SD = "2026-09-03"

def hdr_style(ws, nc):
    hf = Font(bold=True, color="FFFFFF", size=11)
    hfill = PatternFill("solid", fgColor="2F5496")
    ha = Alignment(horizontal="center", vertical="center", wrap_text=True)
    bd = Border(left=Side('thin'), right=Side('thin'), top=Side('thin'), bottom=Side('thin'))
    for c in range(1, nc+1):
        cell = ws.cell(1, c); cell.font=hf; cell.fill=hfill; cell.alignment=ha; cell.border=bd
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, max_col=nc):
        for cell in row:
            cell.border=bd; cell.alignment=Alignment(vertical="center", wrap_text=True)
    ws.freeze_panes="A2"

def autow(ws, mx=55):
    for col in ws.columns:
        ml=0; cl=col[0].column_letter
        for cell in col:
            if cell.value:
                v=str(cell.value); l=sum(2 if ord(c)>127 else 1 for c in v); ml=max(ml,l)
        ws.column_dimensions[cl].width=min(ml+4, mx)

# ============================================================
# 1. phone_specs.xlsx — 按版本拆分 specifications
# ============================================================
# products 不变
products = [
    ("APPLE_IPHONE_16","Apple","iPhone 16","iPhone","2024-09","https://www.apple.com.cn/iphone-16/",SD),
    ("APPLE_IPHONE_16_PRO","Apple","iPhone 16 Pro","iPhone Pro","2024-09","https://www.apple.com.cn/iphone-16-pro/",SD),
    ("APPLE_IPHONE_15","Apple","iPhone 15","iPhone","2023-09","https://www.apple.com.cn/iphone-15/",SD),
    ("HUAWEI_MATE_60","华为","Mate 60","Mate 系列","2023-08","https://www.huawei.com/cn/phones/mate-60",SD),
    ("HUAWEI_MATE_70","华为","Mate 70","Mate 系列","2024-11","https://www.huawei.com/cn/phones/mate-70",SD),
    ("HUAWEI_PURA_70","华为","Pura 70","Pura 系列","2024-04","https://www.huawei.com/cn/phones/pura-70",SD),
    ("XIAOMI_14","小米","小米 14","小米数字系列","2023-10","https://www.mi.com/xiaomi-14",SD),
    ("XIAOMI_15","小米","小米 15","小米数字系列","2024-10","https://www.mi.com/xiaomi-15",SD),
    ("XIAOMI_15_ULTRA","小米","小米 15 Ultra","小米数字系列 Ultra","2025-02","https://www.mi.com/xiaomi-15-ultra",SD),
]

# specifications: 每个存储版本一行
# variant_id, product_id, ram, storage, color, processor, screen_size, screen_type,
# refresh_rate, resolution, rear_camera, front_camera, battery, charging_wired,
# charging_wireless, network, wifi, bluetooth, nfc, dual_sim, weight, dimensions,
# waterproof, operating_system
spec_rows = []
def add_spec(vid, pid, ram, storage, color, proc, ss, st, rr, res, rear, front, bat, cw, cwl, net, wifi, bt, nfc, ds, w, dim, wp, os):
    spec_rows.append((vid,pid,ram,storage,color,proc,ss,st,rr,res,rear,front,bat,cw,cwl,net,wifi,bt,nfc,ds,w,dim,wp,os))

IP16_COLORS = "黑色、白色、粉色、群青色、深青色"
IP16P_COLORS = "白色钛金属、黑色钛金属、原色钛金属、沙漠钛金属"
IP15_COLORS = "粉色、黄色、绿色、蓝色、黑色"
M60_COLORS = "雅川青、白沙银、南糯紫、雅丹黑"
M70_COLORS = "云杉绿、曜石黑、雪域白、风信紫"
P70_COLORS = "羽砂白、羽砂黑、樱玫红、薰衣草紫、冰雪蓝"
MI14_COLORS = "黑色、白色、岩石青、雪山粉"
MI15_COLORS = "黑色、白色、浅草绿、丁香紫"
MI15U_COLORS = "黑色、白色、钛金属特别版"

IP_DS_CN = "中国大陆版：双实体 Nano-SIM 双卡双待；海外版：eSIM + 实体 SIM 或双 eSIM"
HW_DS = "双实体 Nano-SIM 双卡双待双通"
MI_DS = "双实体 Nano-SIM 双卡双待"

# iPhone 16 - 3 versions
for stg in ["128GB","256GB","512GB"]:
    add_spec(f"APPLE_IPHONE_16_{stg.replace('GB','')}","APPLE_IPHONE_16","官方未公布",stg,IP16_COLORS,
        "A18","6.1 英寸","OLED 超视网膜 XDR 显示屏","60Hz","2556×1179",
        "4800 万像素主摄 + 1200 万像素超广角","1200 万像素","官方未公布",
        "USB-C，最高 20W 有线快充","支持 MagSafe 无线充电（最高 15W）",
        "5G（Sub-6GHz）","Wi-Fi 6E（802.11ax）","蓝牙 5.3","支持",IP_DS_CN,
        "170g","147.6×71.6×7.8mm","IP68","iOS 18")

# iPhone 16 Pro - 4 versions
for stg in ["128GB","256GB","512GB","1TB"]:
    add_spec(f"APPLE_IPHONE_16_PRO_{stg.replace('GB','').replace('1TB','1024')}","APPLE_IPHONE_16_PRO","官方未公布",stg,IP16P_COLORS,
        "A18 Pro","6.3 英寸","OLED 超视网膜 XDR 显示屏，ProMotion 自适应刷新率","120Hz","2622×1206",
        "4800 万像素主摄（第二代）+ 4800 万像素超广角 + 1200 万像素 5 倍潜望长焦","1200 万像素","官方未公布",
        "USB-C","支持 MagSafe 无线充电（最高 15W）",
        "5G（Sub-6GHz）","Wi-Fi 7（802.11be）","蓝牙 5.3","支持",IP_DS_CN,
        "199g","149.6×71.5×8.25mm","IP68","iOS 18")

# iPhone 15 - 3 versions
for stg in ["128GB","256GB","512GB"]:
    add_spec(f"APPLE_IPHONE_15_{stg.replace('GB','')}","APPLE_IPHONE_15","官方未公布",stg,IP15_COLORS,
        "A16 仿生","6.1 英寸","OLED 超视网膜 XDR 显示屏","60Hz","2556×1179",
        "4800 万像素主摄 + 1200 万像素超广角","1200 万像素","官方未公布",
        "USB-C，最高 20W 有线快充","支持 MagSafe 无线充电（最高 15W）",
        "5G（Sub-6GHz）","Wi-Fi 6（802.11ax）","蓝牙 5.3","支持",IP_DS_CN,
        "171g","147.6×71.6×7.8mm","IP68","iOS 17（可升级）")

# Huawei Mate 60 - 3 versions
for stg in ["256GB","512GB","1TB"]:
    add_spec(f"HUAWEI_MATE_60_12_{stg.replace('GB','').replace('1TB','1024')}","HUAWEI_MATE_60","12GB",stg,M60_COLORS,
        "麒麟 9000S","6.69 英寸","OLED，第二代昆仑玻璃","120Hz","2688×1216",
        "5000 万像素超光变主摄（F1.4-F4.0 可变光圈，OIS）+ 1200 万像素超广角 + 1200 万像素潜望长焦","1300 万像素","4750mAh",
        "66W 有线超级快充","50W 无线超级快充",
        "5G，支持北斗卫星消息","Wi-Fi 6（802.11ax）","蓝牙 5.2","支持",HW_DS,
        "209g","161.4×76×7.95mm","IP68","HarmonyOS 4.0")

# Huawei Mate 70 - 3 versions
for stg in ["256GB","512GB","1TB"]:
    add_spec(f"HUAWEI_MATE_70_12_{stg.replace('GB','').replace('1TB','1024')}","HUAWEI_MATE_70","12GB",stg,M70_COLORS,
        "麒麟 9010","6.7 英寸","OLED 直面屏，第二代昆仑玻璃","120Hz","2688×1216",
        "5000 万像素主摄（F1.4-F4.0 可变光圈，OIS）+ 4000 万像素超广角 + 1200 万像素潜望长焦 + 150 万像素红枫原色多光谱","1300 万像素","5300mAh",
        "66W 有线超级快充","50W 无线超级快充",
        "5G，支持北斗卫星消息、星闪","Wi-Fi 6（802.11ax）","蓝牙 5.2","支持",HW_DS,
        "203g","160.9×76×7.8mm","IP68（4米抗水）/ IP69","HarmonyOS 4.3")

# Huawei Pura 70 - 3 versions
for stg in ["256GB","512GB","1TB"]:
    add_spec(f"HUAWEI_PURA_70_12_{stg.replace('GB','').replace('1TB','1024')}","HUAWEI_PURA_70","12GB",stg,P70_COLORS,
        "麒麟 9000S1","6.6 英寸","OLED 直屏，第二代昆仑玻璃","1-120Hz LTPO","2760×1256",
        "5000 万像素超聚光主摄（F1.4-F4.0 可变光圈，OIS）+ 1300 万像素超广角","1300 万像素","4900mAh",
        "66W 有线超级快充","50W 无线超级快充",
        "5G","Wi-Fi 6（802.11ax）","蓝牙 5.2","支持",HW_DS,
        "207g","157.6×74.3×7.95mm","IP68","HarmonyOS 4.2")

# Xiaomi 14 - 5 versions
mi14_vers = [("8GB","256GB"),("12GB","256GB"),("12GB","512GB"),("16GB","512GB"),("16GB","1TB")]
for ram,stg in mi14_vers:
    add_spec(f"XIAOMI_14_{ram.replace('GB','')}_{stg.replace('GB','').replace('1TB','1024')}","XIAOMI_14",ram,stg,MI14_COLORS,
        "骁龙 8 Gen3","6.36 英寸","OLED 柔性直屏，C8 发光材料","1-120Hz LTPO","2670×1200",
        "5000 万像素徕卡主摄（f/1.6，OIS）+ 5000 万像素超广角 + 5000 万像素长焦（75mm，3.2x）","3200 万像素","4610mAh",
        "90W 有线快充","50W 无线快充",
        "5G","Wi-Fi 6E（802.11ax）","蓝牙 5.4","支持",MI_DS,
        "193g（玻璃版）/ 188g（素皮版）","152.8×71.5×8.20mm（玻璃版）","IP68","小米澎湃 OS")

# Xiaomi 15 - 4 versions
mi15_vers = [("12GB","256GB"),("12GB","512GB"),("16GB","512GB"),("16GB","1TB")]
for ram,stg in mi15_vers:
    add_spec(f"XIAOMI_15_{ram.replace('GB','')}_{stg.replace('GB','').replace('1TB','1024')}","XIAOMI_15",ram,stg,MI15_COLORS,
        "骁龙 8 至尊版","6.36 英寸","OLED 直屏","1-120Hz LTPO","2670×1200",
        "5000 万像素徕卡主摄（光影猎人 900，f/1.62，OIS）+ 5000 万像素超广角 + 5000 万像素徕卡浮动长焦（60mm，2.6x）","3200 万像素","5400mAh",
        "90W 有线快充","50W 无线快充（磁吸）",
        "5G","Wi-Fi 7（802.11be）","蓝牙 5.4","支持",MI_DS,
        "191g","152.3×71.2×8.08mm","IP68","Xiaomi HyperOS 2")

# Xiaomi 15 Ultra - 3 versions
mi15u_vers = [("12GB","256GB"),("16GB","512GB"),("16GB","1TB")]
for ram,stg in mi15u_vers:
    add_spec(f"XIAOMI_15_ULTRA_{ram.replace('GB','')}_{stg.replace('GB','').replace('1TB','1024')}","XIAOMI_15_ULTRA",ram,stg,MI15U_COLORS,
        "骁龙 8 至尊版","6.73 英寸","OLED 全等深微曲面屏，小米龙晶玻璃 2.0","1-120Hz LTPO","3200×1440",
        "5000 万像素主摄（索尼 LYT-900，1 英寸，f/1.63，OIS）+ 5000 万像素超广角 + 5000 万像素长焦 + 2 亿像素潜望长焦（5x）","3200 万像素","6000mAh",
        "90W 有线快充","80W 无线闪充",
        "5G，支持天通卫星通话 + 北斗卫星短信","Wi-Fi 7（802.11be）","蓝牙 5.4","支持",MI_DS,
        "226g","161.4×75.6×8.65mm","IP68","Xiaomi HyperOS")

# variants: variant_id, product_id, version, official_price, currency, price_type, source_url, effective_date
variant_rows = [
    ("APPLE_IPHONE_16_128","APPLE_IPHONE_16","128GB",5999,"CNY","官方建议零售价","https://www.apple.com.cn/iphone-16/",SD),
    ("APPLE_IPHONE_16_256","APPLE_IPHONE_16","256GB",6999,"CNY","官方建议零售价","https://www.apple.com.cn/iphone-16/",SD),
    ("APPLE_IPHONE_16_512","APPLE_IPHONE_16","512GB",8999,"CNY","官方建议零售价","https://www.apple.com.cn/iphone-16/",SD),
    ("APPLE_IPHONE_16_PRO_128","APPLE_IPHONE_16_PRO","128GB",7999,"CNY","官方建议零售价","https://www.apple.com.cn/iphone-16-pro/",SD),
    ("APPLE_IPHONE_16_PRO_256","APPLE_IPHONE_16_PRO","256GB",8999,"CNY","官方建议零售价","https://www.apple.com.cn/iphone-16-pro/",SD),
    ("APPLE_IPHONE_16_PRO_512","APPLE_IPHONE_16_PRO","512GB",10999,"CNY","官方建议零售价","https://www.apple.com.cn/iphone-16-pro/",SD),
    ("APPLE_IPHONE_16_PRO_1024","APPLE_IPHONE_16_PRO","1TB",12999,"CNY","官方建议零售价","https://www.apple.com.cn/iphone-16-pro/",SD),
    ("APPLE_IPHONE_15_128","APPLE_IPHONE_15","128GB",5999,"CNY","官方建议零售价（首发价）","https://www.apple.com.cn/iphone-15/",SD),
    ("APPLE_IPHONE_15_256","APPLE_IPHONE_15","256GB",6999,"CNY","官方建议零售价（首发价）","https://www.apple.com.cn/iphone-15/",SD),
    ("APPLE_IPHONE_15_512","APPLE_IPHONE_15","512GB",8999,"CNY","官方建议零售价（首发价）","https://www.apple.com.cn/iphone-15/",SD),
    ("HUAWEI_MATE_60_12_256","HUAWEI_MATE_60","12GB+256GB",5499,"CNY","官方建议零售价（首发价）","https://www.huawei.com/cn/phones/mate-60",SD),
    ("HUAWEI_MATE_60_12_512","HUAWEI_MATE_60","12GB+512GB",6499,"CNY","官方建议零售价（首发价）","https://www.huawei.com/cn/phones/mate-60",SD),
    ("HUAWEI_MATE_60_12_1024","HUAWEI_MATE_60","12GB+1TB",7499,"CNY","官方建议零售价（首发价）","https://www.huawei.com/cn/phones/mate-60",SD),
    ("HUAWEI_MATE_70_12_256","HUAWEI_MATE_70","12GB+256GB",5499,"CNY","官方建议零售价","https://www.huawei.com/cn/phones/mate-70",SD),
    ("HUAWEI_MATE_70_12_512","HUAWEI_MATE_70","12GB+512GB",5999,"CNY","官方建议零售价","https://www.huawei.com/cn/phones/mate-70",SD),
    ("HUAWEI_MATE_70_12_1024","HUAWEI_MATE_70","12GB+1TB",6999,"CNY","官方建议零售价","https://www.huawei.com/cn/phones/mate-70",SD),
    ("HUAWEI_PURA_70_12_256","HUAWEI_PURA_70","12GB+256GB",5499,"CNY","官方建议零售价","https://www.huawei.com/cn/phones/pura-70",SD),
    ("HUAWEI_PURA_70_12_512","HUAWEI_PURA_70","12GB+512GB",5999,"CNY","官方建议零售价","https://www.huawei.com/cn/phones/pura-70",SD),
    ("HUAWEI_PURA_70_12_1024","HUAWEI_PURA_70","12GB+1TB",6999,"CNY","官方建议零售价","https://www.huawei.com/cn/phones/pura-70",SD),
    ("XIAOMI_14_8_256","XIAOMI_14","8GB+256GB",3999,"CNY","官方建议零售价（首发价）","https://www.mi.com/xiaomi-14",SD),
    ("XIAOMI_14_12_256","XIAOMI_14","12GB+256GB",4299,"CNY","官方建议零售价（首发价）","https://www.mi.com/xiaomi-14",SD),
    ("XIAOMI_14_12_512","XIAOMI_14","12GB+512GB",4599,"CNY","官方建议零售价（首发价）","https://www.mi.com/xiaomi-14",SD),
    ("XIAOMI_14_16_512","XIAOMI_14","16GB+512GB",4899,"CNY","官方建议零售价（首发价）","https://www.mi.com/xiaomi-14",SD),
    ("XIAOMI_14_16_1024","XIAOMI_14","16GB+1TB",5299,"CNY","官方建议零售价（首发价）","https://www.mi.com/xiaomi-14",SD),
    ("XIAOMI_15_12_256","XIAOMI_15","12GB+256GB",4499,"CNY","官方建议零售价","https://www.mi.com/xiaomi-15",SD),
    ("XIAOMI_15_12_512","XIAOMI_15","12GB+512GB",4799,"CNY","官方建议零售价","https://www.mi.com/xiaomi-15",SD),
    ("XIAOMI_15_16_512","XIAOMI_15","16GB+512GB",4999,"CNY","官方建议零售价","https://www.mi.com/xiaomi-15",SD),
    ("XIAOMI_15_16_1024","XIAOMI_15","16GB+1TB",5499,"CNY","官方建议零售价","https://www.mi.com/xiaomi-15",SD),
    ("XIAOMI_15_ULTRA_12_256","XIAOMI_15_ULTRA","12GB+256GB",6499,"CNY","官方建议零售价","https://www.mi.com/xiaomi-15-ultra",SD),
    ("XIAOMI_15_ULTRA_16_512","XIAOMI_15_ULTRA","16GB+512GB",6999,"CNY","官方建议零售价","https://www.mi.com/xiaomi-15-ultra",SD),
    ("XIAOMI_15_ULTRA_16_1024","XIAOMI_15_ULTRA","16GB+1TB",7799,"CNY","官方建议零售价","https://www.mi.com/xiaomi-15-ultra",SD),
]

wb = openpyxl.Workbook()
ws = wb.active; ws.title="products"
ws.append(["product_id","brand","model","series","release_date","official_url","source_date"])
for r in products: ws.append(r)
hdr_style(ws,7); autow(ws)

ws2 = wb.create_sheet("specifications")
spec_h = ["variant_id","product_id","ram","storage","color","processor","screen_size","screen_type",
    "refresh_rate","resolution","rear_camera","front_camera","battery","charging_wired",
    "charging_wireless","network","wifi","bluetooth","nfc","dual_sim","weight","dimensions",
    "waterproof","operating_system"]
ws2.append(spec_h)
for r in spec_rows: ws2.append(r)
hdr_style(ws2,len(spec_h)); autow(ws2)

ws3 = wb.create_sheet("variants")
ws3.append(["variant_id","product_id","version","official_price","currency","price_type","source_url","effective_date"])
for r in variant_rows: ws3.append(r)
hdr_style(ws3,8); autow(ws3)
wb.save(os.path.join(BASE,"phone_specs.xlsx"))
print(f"phone_specs.xlsx: products={len(products)}, specs={len(spec_rows)}, variants={len(variant_rows)}")

# ============================================================
# 2. sources.xlsx — 增强字段
# ============================================================
sources = [
    ("SRC001","APPLE_IPHONE_16","品牌官网","https://www.apple.com.cn/iphone-16/","iPhone 16 - Apple (中国大陆)",SD,"是","全版本",1,"中国大陆","已核验",""),
    ("SRC002","APPLE_IPHONE_16_PRO","品牌官网","https://www.apple.com.cn/iphone-16-pro/","iPhone 16 Pro - Apple (中国大陆)",SD,"是","全版本",1,"中国大陆","已核验",""),
    ("SRC003","APPLE_IPHONE_15","品牌官网","https://www.apple.com.cn/iphone-15/","iPhone 15 - Apple (中国大陆)",SD,"是","全版本",1,"中国大陆","已核验",""),
    ("SRC004","HUAWEI_MATE_60","品牌官网","https://www.huawei.com/cn/phones/mate-60","HUAWEI Mate 60 规格参数",SD,"是","全版本",1,"中国大陆","已核验",""),
    ("SRC005","HUAWEI_MATE_70","品牌官网","https://www.huawei.com/cn/phones/mate-70","HUAWEI Mate 70 规格参数",SD,"是","全版本",1,"中国大陆","已核验",""),
    ("SRC006","HUAWEI_PURA_70","品牌官网","https://www.huawei.com/cn/phones/pura-70","HUAWEI Pura 70 规格参数",SD,"是","全版本",1,"中国大陆","已核验",""),
    ("SRC007","XIAOMI_14","品牌官网","https://www.mi.com/xiaomi-14","小米 14 规格参数",SD,"是","全版本",1,"中国大陆","已核验",""),
    ("SRC008","XIAOMI_15","品牌官网","https://www.mi.com/xiaomi-15","小米 15 规格参数",SD,"是","全版本",1,"中国大陆","已核验",""),
    ("SRC009","XIAOMI_15_ULTRA","品牌官网","https://www.mi.com/xiaomi-15-ultra","小米 15 Ultra 规格参数",SD,"是","全版本",1,"中国大陆","已核验",""),
    ("SRC010","APPLE_IPHONE_16","可靠第三方","https://detail.zol.com.cn/cell_phone/index2105467.shtml","苹果 iPhone 16 参数 - 中关村在线",SD,"否","全版本",4,"中国大陆","已核验","配色以官网5色为准，第三方部分页面列出6色含沙漠色为误标"),
    ("SRC011","APPLE_IPHONE_16_PRO","可靠第三方","https://detail.zol.com.cn/cell_phone/index2105469.shtml","苹果 iPhone 16 Pro 参数 - 中关村在线",SD,"否","全版本",4,"中国大陆","已核验",""),
    ("SRC012","APPLE_IPHONE_15","可靠第三方","https://detail.zol.com.cn/cell_phone/index1896188.shtml","苹果 iPhone 15 参数 - 中关村在线",SD,"否","全版本",4,"中国大陆","已核验",""),
    ("SRC013","HUAWEI_MATE_60","可靠第三方","https://detail.zol.com.cn/series/57/613/param_10717238_0_1.html","华为 Mate 60 系列参数 - 中关村在线",SD,"否","全版本",4,"中国大陆","已核验",""),
    ("SRC014","HUAWEI_MATE_70","可靠第三方","https://detail.zol.com.cn/2115/2114263/param.shtml","华为 Mate 70 参数 - 中关村在线",SD,"否","12GB+256GB",4,"中国大陆","已核验","Wi-Fi 标准版为Wi-Fi 6，Pro+才支持Wi-Fi 7"),
    ("SRC015","HUAWEI_PURA_70","可靠第三方","https://detail.zol.com.cn/cell_phone/index1986304.shtml","华为 Pura 70 参数 - 中关村在线",SD,"否","全版本",4,"中国大陆","已核验",""),
    ("SRC016","XIAOMI_14","可靠第三方","https://detail.zol.com.cn/series/57/34645/param_10723611_0_1.html","小米 14 系列参数 - 中关村在线",SD,"否","全版本",4,"中国大陆","已核验",""),
    ("SRC017","XIAOMI_15","可靠第三方","https://detail.zol.com.cn/2113/2112056/param.shtml","小米 15 参数 - 中关村在线",SD,"否","16GB+1TB",4,"中国大陆","已核验",""),
    ("SRC018","XIAOMI_15_ULTRA","可靠第三方","https://detail.zol.com.cn/2122/2121272/param.shtml","小米 15 Ultra 参数 - 中关村在线",SD,"否","12GB+256GB",4,"中国大陆","已核验",""),
]
wb2 = openpyxl.Workbook()
ws4 = wb2.active; ws4.title="sources"
sh = ["source_id","product_id","source_type","source_url","page_title","fetch_date","is_official","applicable_version","source_priority","region","data_status","conflict_note"]
ws4.append(sh)
for r in sources: ws4.append(r)
hdr_style(ws4,len(sh)); autow(ws4)
wb2.save(os.path.join(BASE,"sources.xlsx"))
print(f"sources.xlsx: {len(sources)} rows")

print("Excel files done.")
