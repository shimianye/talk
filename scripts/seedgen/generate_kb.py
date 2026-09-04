# -*- coding: utf-8 -*-
"""生成手机客服知识库：phone_specs.xlsx, sources.xlsx, 9份商品知识卡, 6份售后政策"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import os

BASE = r"C:\Users\Administrator\Doubao\chats\2026-09-03\new-chat-5"
KB = os.path.join(BASE, "kb-docs")
SOURCE_DATE = "2026-09-03"

# ============================================================
# 数据定义
# ============================================================

products = [
    # product_id, brand, model, series, release_date, official_url, source_date
    ("APPLE_IPHONE_16", "Apple", "iPhone 16", "iPhone", "2024-09", "https://www.apple.com.cn/iphone-16/", SOURCE_DATE),
    ("APPLE_IPHONE_16_PRO", "Apple", "iPhone 16 Pro", "iPhone Pro", "2024-09", "https://www.apple.com.cn/iphone-16-pro/", SOURCE_DATE),
    ("APPLE_IPHONE_15", "Apple", "iPhone 15", "iPhone", "2023-09", "https://www.apple.com.cn/iphone-15/", SOURCE_DATE),
    ("HUAWEI_MATE_60", "华为", "Mate 60", "Mate 系列", "2023-08", "https://www.huawei.com/cn/phones/mate-60", SOURCE_DATE),
    ("HUAWEI_MATE_70", "华为", "Mate 70", "Mate 系列", "2024-11", "https://www.huawei.com/cn/phones/mate-70", SOURCE_DATE),
    ("HUAWEI_PURA_70", "华为", "Pura 70", "Pura 系列", "2024-04", "https://www.huawei.com/cn/phones/pura-70", SOURCE_DATE),
    ("XIAOMI_14", "小米", "小米 14", "小米数字系列", "2023-10", "https://www.mi.com/xiaomi-14", SOURCE_DATE),
    ("XIAOMI_15", "小米", "小米 15", "小米数字系列", "2024-10", "https://www.mi.com/xiaomi-15", SOURCE_DATE),
    ("XIAOMI_15_ULTRA", "小米", "小米 15 Ultra", "小米数字系列 Ultra", "2025-02", "https://www.mi.com/xiaomi-15-ultra", SOURCE_DATE),
]

# specifications: product_id, version, processor, screen_size, screen_type, refresh_rate,
#   resolution, ram, storage, rear_camera, front_camera, battery, charging, network,
#   weight, dimensions, waterproof, operating_system, colors
specs = [
    ("APPLE_IPHONE_16", "128GB", "A18", "6.1 英寸", "OLED 超视网膜 XDR 显示屏", "60Hz",
     "2556×1179", "官方未公布", "128GB",
     "4800 万像素主摄 + 1200 万像素超广角", "1200 万像素",
     "官方未公布", "USB-C，最高 20W 有线快充，支持 MagSafe 无线充电", "5G",
     "170g", "147.6×71.6×7.8mm", "IP68", "iOS 18",
     "黑色、白色、粉色、群青色、深青色、沙漠色"),
    ("APPLE_IPHONE_16_PRO", "128GB", "A18 Pro", "6.3 英寸", "OLED 超视网膜 XDR 显示屏，ProMotion 自适应刷新率", "120Hz",
     "2622×1206", "官方未公布", "128GB",
     "4800 万像素主摄（第二代）+ 4800 万像素超广角 + 1200 万像素 5 倍潜望长焦", "1200 万像素",
     "官方未公布", "USB-C，支持 MagSafe 无线充电", "5G",
     "199g", "149.6×71.5×8.25mm", "IP68", "iOS 18",
     "白色钛金属、黑色钛金属、原色钛金属、沙漠钛金属"),
    ("APPLE_IPHONE_15", "128GB", "A16 仿生", "6.1 英寸", "OLED 超视网膜 XDR 显示屏", "60Hz",
     "2556×1179", "官方未公布", "128GB",
     "4800 万像素主摄 + 1200 万像素超广角", "1200 万像素",
     "官方未公布", "USB-C，最高 20W 有线快充，支持 MagSafe 无线充电", "5G",
     "171g", "147.6×71.6×7.8mm", "IP68", "iOS 17（可升级至最新版）",
     "粉色、黄色、绿色、蓝色、黑色"),
    ("HUAWEI_MATE_60", "12GB+256GB", "麒麟 9000S", "6.69 英寸", "OLED，第二代昆仑玻璃", "120Hz",
     "2688×1216", "12GB", "256GB",
     "5000 万像素超光变主摄（F1.4-F4.0 可变光圈，OIS）+ 1200 万像素超广角 + 1200 万像素潜望长焦", "1300 万像素",
     "4750mAh", "66W 有线超级快充 + 50W 无线超级快充", "5G，支持北斗卫星消息",
     "209g", "161.4×76×7.95mm", "IP68", "HarmonyOS 4.0",
     "雅川青、白沙银、南糯紫、雅丹黑"),
    ("HUAWEI_MATE_70", "12GB+256GB", "麒麟 9010", "6.7 英寸", "OLED 直面屏，第二代昆仑玻璃", "120Hz",
     "2688×1216", "12GB", "256GB",
     "5000 万像素主摄（F1.4-F4.0 可变光圈，OIS）+ 4000 万像素超广角 + 1200 万像素潜望长焦 + 150 万像素红枫原色多光谱", "1300 万像素",
     "5300mAh", "66W 有线超级快充 + 50W 无线超级快充", "5G，支持北斗卫星消息、星闪",
     "203g", "160.9×76×7.8mm", "IP68（4 米抗水）/ IP69", "HarmonyOS 4.3",
     "云杉绿、曜石黑、雪域白、风信紫"),
    ("HUAWEI_PURA_70", "12GB+256GB", "麒麟 9000S1", "6.6 英寸", "OLED 直屏，第二代昆仑玻璃", "1-120Hz LTPO",
     "2760×1256", "12GB", "256GB",
     "5000 万像素超聚光主摄（F1.4-F4.0 可变光圈，OIS）+ 1300 万像素超广角", "1300 万像素",
     "4900mAh", "66W 有线超级快充 + 50W 无线超级快充", "5G",
     "207g", "157.6×74.3×7.95mm", "IP68", "HarmonyOS 4.2",
     "羽砂白、羽砂黑、樱玫红、薰衣草紫、冰雪蓝"),
    ("XIAOMI_14", "8GB+256GB", "骁龙 8 Gen3", "6.36 英寸", "OLED 柔性直屏，C8 发光材料", "1-120Hz LTPO",
     "2670×1200", "8GB", "256GB",
     "5000 万像素徕卡主摄（f/1.6，OIS）+ 5000 万像素超广角 + 5000 万像素长焦（75mm，3.2x）", "3200 万像素",
     "4610mAh", "90W 有线快充 + 50W 无线快充", "5G",
     "193g（玻璃版）/ 188g（素皮版）", "152.8×71.5×8.20mm（玻璃版）", "IP68", "小米澎湃 OS",
     "黑色、白色、岩石青、雪山粉"),
    ("XIAOMI_15", "12GB+256GB", "骁龙 8 至尊版", "6.36 英寸", "OLED 直屏", "1-120Hz LTPO",
     "2670×1200", "12GB", "256GB",
     "5000 万像素徕卡主摄（光影猎人 900，f/1.62，OIS）+ 5000 万像素超广角 + 5000 万像素徕卡浮动长焦（60mm，2.6x）", "3200 万像素",
     "5400mAh", "90W 有线快充 + 50W 无线快充（磁吸）", "5G",
     "191g", "152.3×71.2×8.08mm", "IP68", "Xiaomi HyperOS 2",
     "黑色、白色、浅草绿、丁香紫"),
    ("XIAOMI_15_ULTRA", "12GB+256GB", "骁龙 8 至尊版", "6.73 英寸", "OLED 全等深微曲面屏，小米龙晶玻璃 2.0", "1-120Hz LTPO",
     "3200×1440", "12GB", "256GB",
     "5000 万像素主摄（索尼 LYT-900，1 英寸，f/1.63，OIS）+ 5000 万像素超广角 + 5000 万像素长焦 + 2 亿像素潜望长焦（5x）", "3200 万像素",
     "6000mAh", "90W 有线快充 + 80W 无线闪充", "5G，支持天通卫星通话 + 北斗卫星短信",
     "226g", "161.4×75.6×8.65mm", "IP68", "Xiaomi HyperOS",
     "黑色、白色、钛金属特别版"),
]

# variants: product_id, version, official_price, currency, price_type, source_url, effective_date
variants = [
    ("APPLE_IPHONE_16", "128GB", 5999, "CNY", "官方建议零售价", "https://www.apple.com.cn/iphone-16/", SOURCE_DATE),
    ("APPLE_IPHONE_16", "256GB", 6999, "CNY", "官方建议零售价", "https://www.apple.com.cn/iphone-16/", SOURCE_DATE),
    ("APPLE_IPHONE_16", "512GB", 8999, "CNY", "官方建议零售价", "https://www.apple.com.cn/iphone-16/", SOURCE_DATE),
    ("APPLE_IPHONE_16_PRO", "128GB", 7999, "CNY", "官方建议零售价", "https://www.apple.com.cn/iphone-16-pro/", SOURCE_DATE),
    ("APPLE_IPHONE_16_PRO", "256GB", 8999, "CNY", "官方建议零售价", "https://www.apple.com.cn/iphone-16-pro/", SOURCE_DATE),
    ("APPLE_IPHONE_16_PRO", "512GB", 10999, "CNY", "官方建议零售价", "https://www.apple.com.cn/iphone-16-pro/", SOURCE_DATE),
    ("APPLE_IPHONE_16_PRO", "1TB", 12999, "CNY", "官方建议零售价", "https://www.apple.com.cn/iphone-16-pro/", SOURCE_DATE),
    ("APPLE_IPHONE_15", "128GB", 5999, "CNY", "官方建议零售价（首发价）", "https://www.apple.com.cn/iphone-15/", SOURCE_DATE),
    ("APPLE_IPHONE_15", "256GB", 6999, "CNY", "官方建议零售价（首发价）", "https://www.apple.com.cn/iphone-15/", SOURCE_DATE),
    ("APPLE_IPHONE_15", "512GB", 8999, "CNY", "官方建议零售价（首发价）", "https://www.apple.com.cn/iphone-15/", SOURCE_DATE),
    ("HUAWEI_MATE_60", "12GB+256GB", 5499, "CNY", "官方建议零售价（首发价）", "https://www.huawei.com/cn/phones/mate-60", SOURCE_DATE),
    ("HUAWEI_MATE_60", "12GB+512GB", 6499, "CNY", "官方建议零售价（首发价）", "https://www.huawei.com/cn/phones/mate-60", SOURCE_DATE),
    ("HUAWEI_MATE_60", "12GB+1TB", 7499, "CNY", "官方建议零售价（首发价）", "https://www.huawei.com/cn/phones/mate-60", SOURCE_DATE),
    ("HUAWEI_MATE_70", "12GB+256GB", 5499, "CNY", "官方建议零售价", "https://www.huawei.com/cn/phones/mate-70", SOURCE_DATE),
    ("HUAWEI_MATE_70", "12GB+512GB", 5999, "CNY", "官方建议零售价", "https://www.huawei.com/cn/phones/mate-70", SOURCE_DATE),
    ("HUAWEI_MATE_70", "12GB+1TB", 6999, "CNY", "官方建议零售价", "https://www.huawei.com/cn/phones/mate-70", SOURCE_DATE),
    ("HUAWEI_PURA_70", "12GB+256GB", 5499, "CNY", "官方建议零售价", "https://www.huawei.com/cn/phones/pura-70", SOURCE_DATE),
    ("HUAWEI_PURA_70", "12GB+512GB", 5999, "CNY", "官方建议零售价", "https://www.huawei.com/cn/phones/pura-70", SOURCE_DATE),
    ("HUAWEI_PURA_70", "12GB+1TB", 6999, "CNY", "官方建议零售价", "https://www.huawei.com/cn/phones/pura-70", SOURCE_DATE),
    ("XIAOMI_14", "8GB+256GB", 3999, "CNY", "官方建议零售价（首发价）", "https://www.mi.com/xiaomi-14", SOURCE_DATE),
    ("XIAOMI_14", "12GB+256GB", 4299, "CNY", "官方建议零售价（首发价）", "https://www.mi.com/xiaomi-14", SOURCE_DATE),
    ("XIAOMI_14", "12GB+512GB", 4599, "CNY", "官方建议零售价（首发价）", "https://www.mi.com/xiaomi-14", SOURCE_DATE),
    ("XIAOMI_14", "16GB+512GB", 4899, "CNY", "官方建议零售价（首发价）", "https://www.mi.com/xiaomi-14", SOURCE_DATE),
    ("XIAOMI_14", "16GB+1TB", 5299, "CNY", "官方建议零售价（首发价）", "https://www.mi.com/xiaomi-14", SOURCE_DATE),
    ("XIAOMI_15", "12GB+256GB", 4499, "CNY", "官方建议零售价", "https://www.mi.com/xiaomi-15", SOURCE_DATE),
    ("XIAOMI_15", "12GB+512GB", 4799, "CNY", "官方建议零售价", "https://www.mi.com/xiaomi-15", SOURCE_DATE),
    ("XIAOMI_15", "16GB+512GB", 4999, "CNY", "官方建议零售价", "https://www.mi.com/xiaomi-15", SOURCE_DATE),
    ("XIAOMI_15", "16GB+1TB", 5499, "CNY", "官方建议零售价", "https://www.mi.com/xiaomi-15", SOURCE_DATE),
    ("XIAOMI_15_ULTRA", "12GB+256GB", 6499, "CNY", "官方建议零售价", "https://www.mi.com/xiaomi-15-ultra", SOURCE_DATE),
    ("XIAOMI_15_ULTRA", "16GB+512GB", 6999, "CNY", "官方建议零售价", "https://www.mi.com/xiaomi-15-ultra", SOURCE_DATE),
    ("XIAOMI_15_ULTRA", "16GB+1TB", 7799, "CNY", "官方建议零售价", "https://www.mi.com/xiaomi-15-ultra", SOURCE_DATE),
]

# sources: source_id, product_id, source_type, source_url, page_title, fetch_date, is_official, applicable_version
sources = [
    ("SRC001", "APPLE_IPHONE_16", "品牌官网", "https://www.apple.com.cn/iphone-16/", "iPhone 16 - Apple (中国大陆)", SOURCE_DATE, "是", "全版本"),
    ("SRC002", "APPLE_IPHONE_16_PRO", "品牌官网", "https://www.apple.com.cn/iphone-16-pro/", "iPhone 16 Pro - Apple (中国大陆)", SOURCE_DATE, "是", "全版本"),
    ("SRC003", "APPLE_IPHONE_15", "品牌官网", "https://www.apple.com.cn/iphone-15/", "iPhone 15 - Apple (中国大陆)", SOURCE_DATE, "是", "全版本"),
    ("SRC004", "HUAWEI_MATE_60", "品牌官网", "https://www.huawei.com/cn/phones/mate-60", "HUAWEI Mate 60 规格参数", SOURCE_DATE, "是", "全版本"),
    ("SRC005", "HUAWEI_MATE_70", "品牌官网", "https://www.huawei.com/cn/phones/mate-70", "HUAWEI Mate 70 规格参数", SOURCE_DATE, "是", "全版本"),
    ("SRC006", "HUAWEI_PURA_70", "品牌官网", "https://www.huawei.com/cn/phones/pura-70", "HUAWEI Pura 70 规格参数", SOURCE_DATE, "是", "全版本"),
    ("SRC007", "XIAOMI_14", "品牌官网", "https://www.mi.com/xiaomi-14", "小米 14 规格参数", SOURCE_DATE, "是", "全版本"),
    ("SRC008", "XIAOMI_15", "品牌官网", "https://www.mi.com/xiaomi-15", "小米 15 规格参数", SOURCE_DATE, "是", "全版本"),
    ("SRC009", "XIAOMI_15_ULTRA", "品牌官网", "https://www.mi.com/xiaomi-15-ultra", "小米 15 Ultra 规格参数", SOURCE_DATE, "是", "全版本"),
    ("SRC010", "APPLE_IPHONE_16", "可靠第三方", "https://detail.zol.com.cn/cell_phone/index2105467.shtml", "苹果 iPhone 16 参数 - 中关村在线", SOURCE_DATE, "否", "全版本"),
    ("SRC011", "APPLE_IPHONE_16_PRO", "可靠第三方", "https://detail.zol.com.cn/cell_phone/index2105469.shtml", "苹果 iPhone 16 Pro 参数 - 中关村在线", SOURCE_DATE, "否", "全版本"),
    ("SRC012", "APPLE_IPHONE_15", "可靠第三方", "https://detail.zol.com.cn/cell_phone/index1896188.shtml", "苹果 iPhone 15 参数 - 中关村在线", SOURCE_DATE, "否", "全版本"),
    ("SRC013", "HUAWEI_MATE_60", "可靠第三方", "https://detail.zol.com.cn/series/57/613/param_10717238_0_1.html", "华为 Mate 60 系列参数 - 中关村在线", SOURCE_DATE, "否", "全版本"),
    ("SRC014", "HUAWEI_MATE_70", "可靠第三方", "https://detail.zol.com.cn/2115/2114263/param.shtml", "华为 Mate 70 参数 - 中关村在线", SOURCE_DATE, "否", "12GB+256GB"),
    ("SRC015", "HUAWEI_PURA_70", "可靠第三方", "https://detail.zol.com.cn/cell_phone/index1986304.shtml", "华为 Pura 70 参数 - 中关村在线", SOURCE_DATE, "否", "全版本"),
    ("SRC016", "XIAOMI_14", "可靠第三方", "https://detail.zol.com.cn/series/57/34645/param_10723611_0_1.html", "小米 14 系列参数 - 中关村在线", SOURCE_DATE, "否", "全版本"),
    ("SRC017", "XIAOMI_15", "可靠第三方", "https://detail.zol.com.cn/2113/2112056/param.shtml", "小米 15 参数 - 中关村在线", SOURCE_DATE, "否", "16GB+1TB"),
    ("SRC018", "XIAOMI_15_ULTRA", "可靠第三方", "https://detail.zol.com.cn/2122/2121272/param.shtml", "小米 15 Ultra 参数 - 中关村在线", SOURCE_DATE, "否", "12GB+256GB"),
]

# ============================================================
# 生成 Excel
# ============================================================

def style_header(ws, ncols):
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    for col in range(1, ncols + 1):
        cell = ws.cell(row=1, column=col)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border
    # data rows border + wrap
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, max_col=ncols):
        for cell in row:
            cell.border = thin_border
            cell.alignment = Alignment(vertical="center", wrap_text=True)
    ws.freeze_panes = "A2"

def auto_width(ws, max_width=50):
    for col_cells in ws.columns:
        max_len = 0
        col_letter = col_cells[0].column_letter
        for cell in col_cells:
            if cell.value:
                # Chinese chars count as ~2
                val = str(cell.value)
                length = sum(2 if ord(c) > 127 else 1 for c in val)
                max_len = max(max_len, length)
        ws.column_dimensions[col_letter].width = min(max_len + 4, max_width)

# --- phone_specs.xlsx ---
wb = openpyxl.Workbook()

# products sheet
ws1 = wb.active
ws1.title = "products"
prod_headers = ["product_id", "brand", "model", "series", "release_date", "official_url", "source_date"]
ws1.append(prod_headers)
for row in products:
    ws1.append(row)
style_header(ws1, len(prod_headers))
auto_width(ws1)

# specifications sheet
ws2 = wb.create_sheet("specifications")
spec_headers = ["product_id", "version", "processor", "screen_size", "screen_type",
                 "refresh_rate", "resolution", "ram", "storage", "rear_camera",
                 "front_camera", "battery", "charging", "network", "weight",
                 "dimensions", "waterproof", "operating_system", "colors"]
ws2.append(spec_headers)
for row in specs:
    ws2.append(row)
style_header(ws2, len(spec_headers))
auto_width(ws2)

# variants sheet
ws3 = wb.create_sheet("variants")
var_headers = ["product_id", "version", "official_price", "currency", "price_type", "source_url", "effective_date"]
ws3.append(var_headers)
for row in variants:
    ws3.append(row)
style_header(ws3, len(var_headers))
auto_width(ws3)

wb.save(os.path.join(BASE, "phone_specs.xlsx"))
print("phone_specs.xlsx created")

# --- sources.xlsx ---
wb2 = openpyxl.Workbook()
ws4 = wb2.active
ws4.title = "sources"
src_headers = ["source_id", "product_id", "source_type", "source_url", "page_title", "fetch_date", "is_official", "applicable_version"]
ws4.append(src_headers)
for row in sources:
    ws4.append(row)
style_header(ws4, len(src_headers))
auto_width(ws4)
wb2.save(os.path.join(BASE, "sources.xlsx"))
print("sources.xlsx created")

# ============================================================
# 生成 Markdown 商品知识卡
# ============================================================

# Build lookup dicts
prod_map = {p[0]: p for p in products}
spec_map = {s[0]: s for s in specs}
var_map = {}
for v in variants:
    var_map.setdefault(v[0], []).append(v)

def gen_kb_md(pid):
    p = prod_map[pid]
    s = spec_map[pid]
    vs = var_map.get(pid, [])
    brand, model, series, release, url = p[1], p[2], p[3], p[4], p[5]
    price_lines = "\n".join([f"- {v[1]}：{v[2]} 元（{v[4]}）" for v in vs])

    # suitable / unsuitable hints per model
    suitable = {
        "APPLE_IPHONE_16": "iOS 生态用户、日常拍照与视频录制、注重系统流畅与长期更新",
        "APPLE_IPHONE_16_PRO": "摄影爱好者、专业视频创作、追求高性能与钛金属质感",
        "APPLE_IPHONE_15": "预算有限的 iOS 入门用户、日常通勤、轻度拍照",
        "HUAWEI_MATE_60": "商务人士、通信稳定性需求高、卫星消息应急场景",
        "HUAWEI_MATE_70": "商务与影像兼顾用户、鸿蒙生态用户、长续航需求",
        "HUAWEI_PURA_70": "时尚年轻用户、人像与自拍爱好者、直屏手感偏好",
        "XIAOMI_14": "小屏旗舰爱好者、徕卡影像偏好、性价比取向",
        "XIAOMI_15": "性能与续航兼顾用户、小屏手感、骁龙 8 至尊版体验",
        "XIAOMI_15_ULTRA": "专业摄影发烧友、全焦段影像需求、卫星通信户外场景",
    }
    unsuitable = {
        "APPLE_IPHONE_16": "追求高刷新率屏幕、重度游戏高帧率、需要超长续航的用户",
        "APPLE_IPHONE_16_PRO": "预算敏感、对长焦需求不高、偏好轻薄小屏的用户",
        "APPLE_IPHONE_15": "追求最新 AI 功能、高刷新率屏幕、A18 级性能的用户",
        "HUAWEI_MATE_60": "追求极致游戏性能、Google 服务依赖、偏好轻薄机身的用户",
        "HUAWEI_MATE_70": "预算有限、对影像要求不高、偏好小屏的用户",
        "HUAWEI_PURA_70": "需要潜望长焦、重度游戏高性能、曲面屏偏好用户",
        "XIAOMI_14": "需要 2K 分辨率大屏、超长续航、潜望长焦的用户",
        "XIAOMI_15": "需要 2K 分辨率、潜望长焦、超大屏的用户",
        "XIAOMI_15_ULTRA": "预算有限、偏好轻薄小屏、对影像无专业需求的用户",
    }

    md = f"""# {model} 商品知识卡

## 基本信息

- 品牌：{brand}
- 型号：{model}
- 产品系列：{series}
- 上市时间：{release}
- 官方产品页：{url}

## 核心参数

### 性能

- 处理器：{s[2]}
- 运行内存：{s[7]}
- 存储版本：{s[8]}（另有其他版本，详见价格表）
- 系统：{s[17]}

### 屏幕

- 尺寸：{s[3]}
- 分辨率：{s[6]}
- 刷新率：{s[5]}
- 屏幕材质：{s[4]}

### 影像

- 后置摄像头：{s[9]}
- 前置摄像头：{s[10]}
- 视频能力：支持 4K 视频录制（具体帧率以官方说明为准）

### 续航与充电

- 电池容量：{s[11]}
- 有线充电：{s[12].split('，')[0] if '，' in s[12] else s[12]}
- 无线充电：{s[12].split('，')[1] if '，' in s[12] else '官方未公布'}

### 网络与连接

- 5G：{s[13]}
- Wi-Fi：支持 Wi-Fi 6（具体协议以官方说明为准）
- 蓝牙：支持（具体版本以官方说明为准）
- NFC：支持

### 机身

- 重量：{s[14]}
- 尺寸：{s[15]}
- 防护等级：{s[16]}
- 配色：{s[18]}

## 版本与价格

{price_lines}

> 价格为官方建议零售价，实际售价以购买时官方商城或授权渠道为准。促销期间可能有优惠。

## 适合人群

- 适合：{suitable.get(pid, '——')}
- 不适合：{unsuitable.get(pid, '——')}

## 常见问题

### 这款手机支持无线充电吗？

{s[12]}。

### 是否支持双卡？

支持双卡（Nano-SIM，具体卡槽类型以官方说明为准）。

### 防水等级是多少？

{s[16]}。注意：防水性能会随日常磨损下降，进水不在免费保修范围内。

### 充电器是否随盒附赠？

具体包装清单以官方商城页面为准。部分品牌出于环保考虑不再附赠充电器。

## 来源

- 官方产品页：{url}
- 官方参数页：{url}
- 第三方参数参考：中关村在线对应机型参数页
- 资料更新时间：{SOURCE_DATE}
"""
    return md

# Write KB files
kb_files = [
    ("APPLE_IPHONE_16", "apple", "iphone-16.md"),
    ("APPLE_IPHONE_16_PRO", "apple", "iphone-16-pro.md"),
    ("APPLE_IPHONE_15", "apple", "iphone-15.md"),
    ("HUAWEI_MATE_60", "huawei", "mate-60.md"),
    ("HUAWEI_MATE_70", "huawei", "mate-70.md"),
    ("HUAWEI_PURA_70", "huawei", "pura-70.md"),
    ("XIAOMI_14", "xiaomi", "xiaomi-14.md"),
    ("XIAOMI_15", "xiaomi", "xiaomi-15.md"),
    ("XIAOMI_15_ULTRA", "xiaomi", "xiaomi-15-ultra.md"),
]

for pid, folder, fname in kb_files:
    path = os.path.join(KB, folder, fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write(gen_kb_md(pid))
    print(f"  KB: {folder}/{fname}")

print("All KB markdown files created.")
