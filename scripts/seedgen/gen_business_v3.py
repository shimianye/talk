# -*- coding: utf-8 -*-
"""V3: 修正 business_data.xlsx — 订单时间逻辑、售后分类一致性、店铺价格体系、物流拆单"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import os, random
from datetime import datetime, timedelta

BASE = r"C:\Users\Administrator\Doubao\chats\2026-09-03\new-chat-5"
SD = "2026-09-03"
random.seed(42)

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

def autow(ws, mx=50):
    for col in ws.columns:
        ml=0; cl=col[0].column_letter
        for cell in col:
            if cell.value:
                v=str(cell.value); l=sum(2 if ord(c)>127 else 1 for c in v); ml=max(ml,l)
        ws.column_dimensions[cl].width=min(ml+4, mx)

def fmt(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def fmt_date(dt):
    return dt.strftime("%Y-%m-%d")

# ============================================================
# 基础数据
# ============================================================
variant_ids = [
    "APPLE_IPHONE_16_128","APPLE_IPHONE_16_256","APPLE_IPHONE_16_512",
    "APPLE_IPHONE_16_PRO_128","APPLE_IPHONE_16_PRO_256","APPLE_IPHONE_16_PRO_512","APPLE_IPHONE_16_PRO_1024",
    "APPLE_IPHONE_15_128","APPLE_IPHONE_15_256","APPLE_IPHONE_15_512",
    "HUAWEI_MATE_60_12_256","HUAWEI_MATE_60_12_512","HUAWEI_MATE_60_12_1024",
    "HUAWEI_MATE_70_12_256","HUAWEI_MATE_70_12_512","HUAWEI_MATE_70_12_1024",
    "HUAWEI_PURA_70_12_256","HUAWEI_PURA_70_12_512","HUAWEI_PURA_70_12_1024",
    "XIAOMI_14_8_256","XIAOMI_14_12_256","XIAOMI_14_12_512","XIAOMI_14_16_512","XIAOMI_14_16_1024",
    "XIAOMI_15_12_256","XIAOMI_15_12_512","XIAOMI_15_16_512","XIAOMI_15_16_1024",
    "XIAOMI_15_ULTRA_12_256","XIAOMI_15_ULTRA_16_512","XIAOMI_15_ULTRA_16_1024",
]

def get_pid(vid):
    if vid.startswith("APPLE_IPHONE_16_PRO"): return "APPLE_IPHONE_16_PRO"
    elif vid.startswith("APPLE_IPHONE_16"): return "APPLE_IPHONE_16"
    elif vid.startswith("APPLE_IPHONE_15"): return "APPLE_IPHONE_15"
    elif vid.startswith("HUAWEI_MATE_60"): return "HUAWEI_MATE_60"
    elif vid.startswith("HUAWEI_MATE_70"): return "HUAWEI_MATE_70"
    elif vid.startswith("HUAWEI_PURA_70"): return "HUAWEI_PURA_70"
    elif vid.startswith("XIAOMI_14"): return "XIAOMI_14"
    elif vid.startswith("XIAOMI_15_ULTRA"): return "XIAOMI_15_ULTRA"
    elif vid.startswith("XIAOMI_15"): return "XIAOMI_15"

products_name_map = {
    "APPLE_IPHONE_16":"iPhone 16","APPLE_IPHONE_16_PRO":"iPhone 16 Pro","APPLE_IPHONE_15":"iPhone 15",
    "HUAWEI_MATE_60":"华为 Mate 60","HUAWEI_MATE_70":"华为 Mate 70","HUAWEI_PURA_70":"华为 Pura 70",
    "XIAOMI_14":"小米 14","XIAOMI_15":"小米 15","XIAOMI_15_ULTRA":"小米 15 Ultra",
}

# 官方建议零售价
official_prices = {
    "APPLE_IPHONE_16_128":5999,"APPLE_IPHONE_16_256":6999,"APPLE_IPHONE_16_512":8999,
    "APPLE_IPHONE_16_PRO_128":7999,"APPLE_IPHONE_16_PRO_256":8999,"APPLE_IPHONE_16_PRO_512":10999,"APPLE_IPHONE_16_PRO_1024":12999,
    "APPLE_IPHONE_15_128":5999,"APPLE_IPHONE_15_256":6999,"APPLE_IPHONE_15_512":8999,
    "HUAWEI_MATE_60_12_256":5499,"HUAWEI_MATE_60_12_512":6499,"HUAWEI_MATE_60_12_1024":7499,
    "HUAWEI_MATE_70_12_256":5499,"HUAWEI_MATE_70_12_512":5999,"HUAWEI_MATE_70_12_1024":6999,
    "HUAWEI_PURA_70_12_256":5499,"HUAWEI_PURA_70_12_512":5999,"HUAWEI_PURA_70_12_1024":6999,
    "XIAOMI_14_8_256":3999,"XIAOMI_14_12_256":4299,"XIAOMI_14_12_512":4599,"XIAOMI_14_16_512":4899,"XIAOMI_14_16_1024":5299,
    "XIAOMI_15_12_256":4499,"XIAOMI_15_12_512":4799,"XIAOMI_15_16_512":4999,"XIAOMI_15_16_1024":5499,
    "XIAOMI_15_ULTRA_12_256":6499,"XIAOMI_15_ULTRA_16_512":6999,"XIAOMI_15_ULTRA_16_1024":7799,
}

warehouses = ["华东仓（上海）","华南仓（深圳）","华北仓（北京）","西南仓（成都）"]
names = ["张三","李四","王五","赵六","陈七","刘八","周九","吴十","郑十一","孙十二"]
districts = ["岳麓区","芙蓉区","天心区","开福区","雨花区"]
roads = ["麓山南路","五一大道","芙蓉中路","湘江中路","韶山北路"]

wb = openpyxl.Workbook()

# ============================================================
# 1. store_products — 增加价格体系字段
# ============================================================
ws = wb.active; ws.title="store_products"
ws.append(["variant_id","product_id","sku","listing_status","original_price","promotion_price",
           "price_type","promotion_id","price_effective_from","price_effective_to",
           "cost_price","margin_pct","on_shelf_date","category"])

# 价格策略：大部分日常售价=官方价或略低，部分活动价更低，个别缺货渠道价略高
price_strategies = [
    ("日常售价", None, 1.0),      # 原价
    ("日常售价", None, 0.95),     # 日常95折
    ("活动价", "PROMO003", 0.92), # 开学季活动
    ("会员价", "PROMO007", 0.90), # 会员专享
    ("活动价", "PROMO001", 0.93), # 新人券
    ("日常售价", None, 0.97),
    ("渠道价", None, 1.02),       # 缺货渠道溢价
    ("秒杀价", "PROMO006", 0.85), # 秒杀
]

for i, vid in enumerate(variant_ids):
    pid = get_pid(vid)
    orig = official_prices[vid]
    # 状态：大部分在售，iPhone15和Mate60部分版本缺货/下架
    if vid.startswith("APPLE_IPHONE_15") and random.random() < 0.4:
        status = "下架"
    elif vid.startswith("HUAWEI_MATE_60") and random.random() < 0.3:
        status = "缺货"
    else:
        status = "在售"

    if status == "在售":
        strat = random.choice(price_strategies)
        ptype, promo_id, factor = strat
        promo_price = int(orig * factor)
        pfrom = "2026-09-01"
        pto = "2026-09-30" if promo_id else "2026-12-31"
    else:
        ptype = "—"
        promo_id = ""
        promo_price = orig
        pfrom = ""
        pto = ""

    cost = int(orig * random.uniform(0.72, 0.85))
    margin = round((promo_price - cost) / promo_price * 100, 1) if promo_price > 0 else 0

    ws.append([vid, pid, f"SKU-{i+1:04d}", status, orig, promo_price, ptype, promo_id,
               pfrom, pto, cost, margin, SD, "智能手机"])
hdr_style(ws,14); autow(ws)
print(f"store_products: {len(variant_ids)} rows, price fields added")

# ============================================================
# 2. inventory — 不变结构，补充数据
# ============================================================
ws2 = wb.create_sheet("inventory")
ws2.append(["inventory_id","variant_id","warehouse","quantity","available_qty","reserved_qty",
            "safety_stock","last_updated","status"])
inv_id = 1
for vid in variant_ids:
    for wh in random.sample(warehouses, random.randint(2,3)):
        qty = random.randint(0, 500)
        reserved = random.randint(0, min(qty, 50))
        avail = qty - reserved
        status = "充足" if avail > 100 else ("偏低" if avail > 20 else ("缺货" if avail == 0 else "紧张"))
        ws2.append([f"INV-{inv_id:05d}", vid, wh, qty, avail, reserved, 50, SD, status])
        inv_id += 1
hdr_style(ws2,9); autow(ws2)

# ============================================================
# 3. promotions — 不变
# ============================================================
ws3 = wb.create_sheet("promotions")
ws3.append(["promo_id","promo_type","name","description","discount_type","discount_value",
            "min_amount","applicable_products","start_date","end_date","status","stackable"])
promos = [
    ("PROMO001","优惠券","新人满减券","新用户首单满3000减200","满减",200,3000,"全品类","2026-08-01","2026-12-31","进行中","是"),
    ("PROMO002","优惠券","品类券","手机品类满5000减300","满减",300,5000,"智能手机","2026-09-01","2026-09-30","进行中","是"),
    ("PROMO003","满减活动","开学季满减","满4000减150，满6000减300","满减",150,4000,"智能手机","2026-08-20","2026-09-15","进行中","否"),
    ("PROMO004","赠品","购机送配件","购机送手机壳+钢化膜","赠品",0,0,"APPLE_IPHONE_16,APPLE_IPHONE_16_PRO,XIAOMI_15","2026-09-01","2026-09-30","进行中","是"),
    ("PROMO005","以旧换新","以旧换新补贴","旧机回收额外补贴最高500元","补贴",500,0,"全品类","2026-08-01","2026-12-31","进行中","是"),
    ("PROMO006","秒杀","限时秒杀","小米14 12+256GB 秒杀价3699","直降",600,0,"XIAOMI_14_12_256","2026-09-10","2026-09-10","未开始","否"),
    ("PROMO007","优惠券","会员专享券","会员满8000减500","满减",500,8000,"智能手机","2026-09-01","2026-10-31","进行中","否"),
    ("PROMO008","赠品","晒单返现","确认收货晒单返50元话费","返现",50,0,"全品类","2026-09-01","2026-12-31","进行中","是"),
]
for p in promos: ws3.append(p)
hdr_style(ws3,12); autow(ws3)

# ============================================================
# 4. orders — 修正时间逻辑：create ≤ pay ≤ ship ≤ receive
# ============================================================
ws4 = wb.create_sheet("orders")
ws4.append(["order_id","user_id","user_name","variant_id","product_name","quantity",
            "unit_price","total_amount","coupon_discount","final_amount","payment_method",
            "order_status","create_time","pay_time","ship_time","receive_time","address"])

statuses = ["待支付","已支付待发货","已发货","已完成","已取消","退款中","已退款"]
status_weights = [5, 12, 22, 38, 5, 10, 8]

base_date = datetime(2026, 8, 1, 9, 0, 0)

for i in range(1, 51):
    vid = random.choice(variant_ids)
    pid = get_pid(vid)
    pname = products_name_map[pid]
    qty = random.choice([1,1,1,1,2])
    price = official_prices[vid]
    total = price * qty
    coupon = random.choice([0,0,0,100,200,300,500])
    final = total - coupon
    status = random.choices(statuses, weights=status_weights)[0]
    uid = f"U{random.randint(1000,9999)}"
    uname = random.choice(names)
    addr = f"湖南省长沙市{random.choice(districts)}{random.choice(roads)}{random.randint(1,500)}号"

    # 生成时间链：create → pay → ship → receive
    create_dt = base_date + timedelta(days=random.randint(0, 30), hours=random.randint(0,12), minutes=random.randint(0,59))
    create_time = fmt(create_dt)

    if status == "待支付":
        pay_time = ""; ship_time = ""; receive_time = ""
    elif status == "已取消":
        # 可能付了又取消，也可能没付就取消
        if random.random() < 0.5:
            pay_dt = create_dt + timedelta(minutes=random.randint(1, 120))
            pay_time = fmt(pay_dt)
        else:
            pay_time = ""
        ship_time = ""; receive_time = ""
    else:
        # 已支付及以上状态都有 pay_time
        pay_dt = create_dt + timedelta(minutes=random.randint(1, 120))
        pay_time = fmt(pay_dt)

        if status in ["已支付待发货"]:
            ship_time = ""; receive_time = ""
        elif status in ["已发货", "退款中", "已退款"]:
            ship_dt = pay_dt + timedelta(hours=random.randint(4, 48))
            ship_time = fmt(ship_dt)
            # 退款中/已退款可能还没收到
            if status in ["已发货"]:
                receive_time = ""
            else:
                # 退款中可能已收到也可能没收到
                if random.random() < 0.5:
                    receive_dt = ship_dt + timedelta(days=random.randint(1, 5))
                    receive_time = fmt(receive_dt)
                else:
                    receive_time = ""
        elif status == "已完成":
            ship_dt = pay_dt + timedelta(hours=random.randint(4, 48))
            ship_time = fmt(ship_dt)
            receive_dt = ship_dt + timedelta(days=random.randint(1, 5))
            receive_time = fmt(receive_dt)
        else:
            ship_time = ""; receive_time = ""

    ws4.append([f"ORD{202609000+i}", uid, uname, vid, pname, qty, price, total, coupon, final,
                random.choice(["支付宝","微信支付","银行卡","花呗分期"]), status,
                create_time, pay_time, ship_time, receive_time, addr])

hdr_style(ws4,17); autow(ws4)

# 验证时间逻辑
time_errors = 0
for row in ws4.iter_rows(min_row=2, max_row=ws4.max_row, values_only=True):
    ct, pt, st, rt = row[12], row[13], row[14], row[15]
    if pt and ct and pt < ct: time_errors += 1
    if st and pt and st < pt: time_errors += 1
    if rt and st and rt < st: time_errors += 1
print(f"orders: 50 rows, time logic errors: {time_errors}")

# ============================================================
# 5. logistics — 增加 package_id, package_count, is_split_shipment
# ============================================================
ws5 = wb.create_sheet("logistics")
ws5.append(["logistics_id","order_id","package_id","package_count","is_split_shipment",
            "carrier","tracking_number","current_status","current_location",
            "estimated_delivery","ship_time","last_update","sign_time"])

carriers = ["顺丰速运","京东物流","中通快递","圆通速递"]
log_statuses = ["已揽收","运输中","派送中","已签收","异常"]

# 选取有ship_time的订单生成物流
order_rows = list(ws4.iter_rows(min_row=2, max_row=ws4.max_row, values_only=True))
shipped_orders = [r for r in order_rows if r[14]]  # has ship_time

log_id = 1
for o in shipped_orders[:30]:
    oid = o[0]
    ship_dt = datetime.strptime(o[14], "%Y-%m-%d %H:%M:%S")
    # 10%概率拆单（多包裹）
    is_split = random.random() < 0.1
    pkg_count = random.randint(2, 3) if is_split else 1

    for pkg_idx in range(1, pkg_count + 1):
        pkg_id = f"PKG-{oid}-{pkg_idx:02d}"
        status = random.choices(log_statuses, weights=[10,30,20,35,5])[0]
        loc = random.choice(["长沙转运中心","上海航空部","深圳集散中心","北京分拣中心",
                             "成都转运中心","长沙岳麓区营业点","派送中"])
        ed = fmt_date(ship_dt + timedelta(days=random.randint(1, 4)))
        lu = fmt(ship_dt + timedelta(hours=random.randint(1, 72)))
        sig = fmt_date(ship_dt + timedelta(days=random.randint(2, 5))) if status == "已签收" else ""

        ws5.append([f"LOG-{log_id:05d}", oid, pkg_id, pkg_count, "是" if is_split else "否",
                    random.choice(carriers), f"SF{random.randint(10000000000,99999999999)}",
                    status, loc, ed, fmt(ship_dt), lu, sig])
        log_id += 1

hdr_style(ws5,13); autow(ws5)
print(f"logistics: {log_id-1} rows, split shipments added")

# ============================================================
# 6. after_sales_cases — 修正分类一致性
# ============================================================
ws6 = wb.create_sheet("after_sales_cases")
ws6.append(["case_id","order_id","user_id","case_type","sub_type","description",
            "status","create_time","resolve_time","resolution","compensation_amount","handler"])

# 定义每种 case_type 对应的 sub_type、description模板、resolution模板
case_templates = {
    "退货": {
        "subs": ["质量问题","七天无理由","发错货","物流破损"],
        "descs": {
            "质量问题": "手机收到后使用两天出现屏幕触控失灵，检测为非人为质量问题，申请退货退款",
            "七天无理由": "手机未激活，包装完好，因个人原因不喜欢，申请七天无理由退货",
            "发错货": "订单购买的是黑色，收到的是白色，颜色发错，申请退货",
            "物流破损": "快递外包装严重破损，手机外壳有磕碰痕迹，申请退货",
        },
        "resos": ["同意退货退款，运费由本店承担","同意退货退款","驳回：商品已激活不支持七天无理由","同意退货，需寄回全部配件"],
    },
    "换货": {
        "subs": ["质量问题","发错货","物流破损"],
        "descs": {
            "质量问题": "手机扬声器无声音，经检测为硬件故障，申请更换新机",
            "发错货": "收到的存储版本与订单不符，订单为256GB，收到128GB，申请换货",
            "物流破损": "运输过程中屏幕碎裂，外包装有明显挤压痕迹，申请更换新机",
        },
        "resos": ["同意换货，3个工作日内发出新机","同意换货","驳回：人为损坏不在换货范围"],
    },
    "维修": {
        "subs": ["屏幕碎裂","电池异常","系统故障","充电异常"],
        "descs": {
            "屏幕碎裂": "手机不慎跌落导致外屏碎裂，触控功能正常，申请付费维修更换屏幕",
            "电池异常": "电池健康度降至75%，一天需充三次电，在保修期内申请免费检测维修",
            "系统故障": "手机频繁自动重启，恢复出厂设置后仍存在，申请售后维修",
            "充电异常": "充电时断时续，更换数据线和充电器后问题依旧，申请维修检测",
        },
        "resos": ["免费维修，已寄回","付费维修，费用599元","驳回：进液导致不在保修范围","维修完成，90天质保"],
    },
    "退款": {
        "subs": ["未发货退款","质量问题退款","重复支付退款"],
        "descs": {
            "未发货退款": "下单后未发货，因个人原因申请取消订单并退款",
            "质量问题退款": "手机存在质量问题，已寄回并验收，申请退款",
            "重复支付退款": "因网络卡顿重复支付了两次，申请退还多付的款项",
        },
        "resos": ["同意退款，1-3个工作日到账","同意退款","驳回：已超过退款时效"],
    },
    "投诉": {
        "subs": ["服务态度","物流问题","商品质量"],
        "descs": {
            "服务态度": "客服回复慢且态度恶劣，多次咨询未得到有效解决，要求投诉并道歉",
            "物流问题": "快递显示已签收但本人未收到，联系快递方无果，要求店铺协助处理",
            "商品质量": "手机使用一周后出现质量问题，售后处理拖延超过7天，要求投诉并加快处理",
        },
        "resos": ["转人工客服主管处理","已联系快递方核实，补偿优惠券50元","致歉并加急处理，补偿100元"],
    },
    "碎屏保障": {
        "subs": ["意外碎屏"],
        "descs": {
            "意外碎屏": "购买了碎屏保障服务，手机意外跌落导致屏幕碎裂，申请免费换屏",
        },
        "resos": ["同意免费换屏，已安排寄修","驳回：已使用过1次碎屏保障","碎屏保障已生效，预计3个工作日完成"],
    },
    "价保": {
        "subs": ["降价补差"],
        "descs": {
            "降价补差": "购买后第5天发现同款商品降价300元，在7天价保期内，申请差价补偿",
        },
        "resos": ["价保补差300元已以优惠券形式发放","驳回：秒杀价不参与价保","核实后补差200元"],
    },
}

paid_orders = [r for r in order_rows if r[13]]  # has pay_time
as_id = 1
for i in range(1, 21):
    o = random.choice(paid_orders)
    oid = o[0]
    uid = o[1]
    ctype = random.choice(list(case_templates.keys()))
    tmpl = case_templates[ctype]
    subtype = random.choice(tmpl["subs"])
    desc = tmpl["descs"][subtype]
    status = random.choices(["待处理","处理中","已完成","已关闭","待用户寄回"], weights=[15,25,35,10,15])[0]

    # 时间：售后创建时间 >= 订单支付时间
    pay_dt = datetime.strptime(o[13], "%Y-%m-%d %H:%M:%S")
    create_dt = pay_dt + timedelta(days=random.randint(1, 15), hours=random.randint(0,12))
    ct = fmt(create_dt)

    if status == "已完成":
        resolve_dt = create_dt + timedelta(days=random.randint(1, 5))
        rt = fmt_date(resolve_dt)
        reso = random.choice(tmpl["resos"])
        comp = random.choice([0,0,0,50,100,200,300]) if ctype in ["投诉","价保"] else 0
    else:
        rt = ""
        reso = ""
        comp = 0

    ws6.append([f"AS-{as_id:05d}", oid, uid, ctype, subtype, desc, status, ct, rt, reso, comp,
                f"客服{random.choice(['A','B','C','D'])}"])
    as_id += 1

hdr_style(ws6,12); autow(ws6)

# 验证售后分类一致性
mismatch = 0
for row in ws6.iter_rows(min_row=2, max_row=ws6.max_row, values_only=True):
    ct, st, desc = row[3], row[4], row[5]
    if ct in case_templates and st in case_templates[ct]["descs"]:
        if desc != case_templates[ct]["descs"][st]:
            # 描述应该匹配模板
            mismatch += 1
    else:
        mismatch += 1
print(f"after_sales_cases: {as_id-1} rows, classification mismatches: {mismatch}")

wb.save(os.path.join(BASE, "business_data.xlsx"))
print("\nbusiness_data.xlsx V3 saved successfully.")
