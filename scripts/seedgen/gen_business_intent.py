# -*- coding: utf-8 -*-
"""生成 business_data.xlsx, intent_taxonomy.xlsx, evaluation_dataset.xlsx"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import os, random

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

# ============================================================
# business_data.xlsx
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
warehouses = ["华东仓（上海）","华南仓（深圳）","华北仓（北京）","西南仓（成都）"]

wb = openpyxl.Workbook()

# --- store_products ---
ws = wb.active; ws.title="store_products"
ws.append(["variant_id","product_id","sku","listing_status","listed_price","cost_price","margin_pct","on_shelf_date","category"])
for i, vid in enumerate(variant_ids):
    pid = "_".join(vid.split("_")[:-1]) if not vid.startswith("APPLE_IPHONE_16_PRO") else "APPLE_IPHONE_16_PRO"
    # fix pid extraction
    if vid.startswith("APPLE_IPHONE_16_PRO"): pid="APPLE_IPHONE_16_PRO"
    elif vid.startswith("APPLE_IPHONE_16"): pid="APPLE_IPHONE_16"
    elif vid.startswith("APPLE_IPHONE_15"): pid="APPLE_IPHONE_15"
    elif vid.startswith("HUAWEI_MATE_60"): pid="HUAWEI_MATE_60"
    elif vid.startswith("HUAWEI_MATE_70"): pid="HUAWEI_MATE_70"
    elif vid.startswith("HUAWEI_PURA_70"): pid="HUAWEI_PURA_70"
    elif vid.startswith("XIAOMI_14"): pid="XIAOMI_14"
    elif vid.startswith("XIAOMI_15_ULTRA"): pid="XIAOMI_15_ULTRA"
    elif vid.startswith("XIAOMI_15"): pid="XIAOMI_15"
    status = "在售" if i not in [7,8,9,10,11,12] else ("下架" if i in [7,8,9] else "缺货")
    # iPhone 15 and Mate 60 some versions out of stock
    listed = random.choice([5999,6999,8999,7999,8999,10999,12999,5999,6999,8999,5499,6499,7499,5499,5999,6999,5499,5999,6999,3999,4299,4599,4899,5299,4499,4799,4999,5499,6499,6999,7799])
    cost = int(listed * random.uniform(0.72, 0.88))
    margin = round((listed-cost)/listed*100, 1)
    ws.append([vid, pid, f"SKU-{i+1:04d}", status, listed, cost, margin, SD, "智能手机"])
hdr_style(ws,9); autow(ws)

# --- inventory ---
ws2 = wb.create_sheet("inventory")
ws2.append(["inventory_id","variant_id","warehouse","quantity","available_qty","reserved_qty","safety_stock","last_updated","status"])
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

# --- promotions ---
ws3 = wb.create_sheet("promotions")
ws3.append(["promo_id","promo_type","name","description","discount_type","discount_value","min_amount","applicable_products","start_date","end_date","status","stackable"])
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

# --- orders ---
ws4 = wb.create_sheet("orders")
ws4.append(["order_id","user_id","user_name","variant_id","product_name","quantity","unit_price","total_amount","coupon_discount","final_amount","payment_method","order_status","create_time","pay_time","ship_time","receive_time","address"])
statuses = ["待支付","已支付待发货","已发货","已完成","已取消","退款中","已退款"]
names = ["张三","李四","王五","赵六","陈七","刘八","周九","吴十","郑十一","孙十二"]
products_name_map = {
    "APPLE_IPHONE_16":"iPhone 16","APPLE_IPHONE_16_PRO":"iPhone 16 Pro","APPLE_IPHONE_15":"iPhone 15",
    "HUAWEI_MATE_60":"华为 Mate 60","HUAWEI_MATE_70":"华为 Mate 70","HUAWEI_PURA_70":"华为 Pura 70",
    "XIAOMI_14":"小米 14","XIAOMI_15":"小米 15","XIAOMI_15_ULTRA":"小米 15 Ultra",
}
for i in range(1, 51):
    vid = random.choice(variant_ids)
    if vid.startswith("APPLE_IPHONE_16_PRO"): pid="APPLE_IPHONE_16_PRO"
    elif vid.startswith("APPLE_IPHONE_16"): pid="APPLE_IPHONE_16"
    elif vid.startswith("APPLE_IPHONE_15"): pid="APPLE_IPHONE_15"
    elif vid.startswith("HUAWEI_MATE_60"): pid="HUAWEI_MATE_60"
    elif vid.startswith("HUAWEI_MATE_70"): pid="HUAWEI_MATE_70"
    elif vid.startswith("HUAWEI_PURA_70"): pid="HUAWEI_PURA_70"
    elif vid.startswith("XIAOMI_14"): pid="XIAOMI_14"
    elif vid.startswith("XIAOMI_15_ULTRA"): pid="XIAOMI_15_ULTRA"
    elif vid.startswith("XIAOMI_15"): pid="XIAOMI_15"
    pname = products_name_map[pid]
    qty = random.choice([1,1,1,1,2])
    price = random.choice([3999,4299,4499,4799,4999,5299,5499,5999,6499,6999,7499,7799,7999,8999,10999,12999])
    total = price * qty
    coupon = random.choice([0,0,0,100,200,300,500])
    final = total - coupon
    status = random.choices(statuses, weights=[5,15,25,35,5,10,5])[0]
    uid = f"U{random.randint(1000,9999)}"
    uname = random.choice(names)
    ct = f"2026-0{random.randint(1,9)}-{random.randint(1,28):02d} {random.randint(9,21):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}"
    pt = ct if status != "待支付" else ""
    st = f"2026-0{random.randint(1,9)}-{random.randint(1,28):02d}" if status in ["已发货","已完成"] else ""
    rt = f"2026-0{random.randint(1,9)}-{random.randint(1,28):02d}" if status == "已完成" else ""
    addr = f"湖南省长沙市{random.choice(['岳麓区','芙蓉区','天心区','开福区','雨花区'])}{random.choice(['麓山南路','五一大道','芙蓉中路','湘江中路'])}XX号"
    ws4.append([f"ORD{202609000+i}", uid, uname, vid, pname, qty, price, total, coupon, final,
                random.choice(["支付宝","微信支付","银行卡","花呗分期"]), status, ct, pt, st, rt, addr])
hdr_style(ws4,17); autow(ws4)

# --- logistics ---
ws5 = wb.create_sheet("logistics")
ws5.append(["logistics_id","order_id","carrier","tracking_number","current_status","current_location","estimated_delivery","ship_time","last_update","sign_time"])
carriers = ["顺丰速运","京东物流","中通快递","圆通速递"]
for i in range(1, 31):
    oid = f"ORD{202609000+random.randint(1,50)}"
    status = random.choices(["已揽收","运输中","派送中","已签收","异常"], weights=[10,35,25,25,5])[0]
    loc = random.choice(["长沙转运中心","上海航空部","深圳集散中心","北京分拣中心","成都转运中心","长沙岳麓区营业点","派送中"])
    ed = f"2026-09-{random.randint(4,10):02d}"
    st = f"2026-09-{random.randint(1,3):02d}"
    lu = f"2026-09-{random.randint(2,4):02d} {random.randint(8,20):02d}:{random.randint(0,59):02d}"
    sig = f"2026-09-{random.randint(4,8):02d}" if status == "已签收" else ""
    ws5.append([f"LOG-{i:05d}", oid, random.choice(carriers), f"SF{random.randint(10000000000,99999999999)}",
                status, loc, ed, st, lu, sig])
hdr_style(ws5,10); autow(ws5)

# --- after_sales_cases ---
ws6 = wb.create_sheet("after_sales_cases")
ws6.append(["case_id","order_id","user_id","case_type","sub_type","description","status","create_time","resolve_time","resolution","compensation_amount","handler"])
case_types = ["退货","换货","维修","退款","投诉","碎屏保障","价保"]
sub_types = ["质量问题","七天无理由","发错货","物流破损","屏幕碎裂","电池异常","系统故障","价格保护","服务态度"]
for i in range(1, 21):
    oid = f"ORD{202609000+random.randint(1,50)}"
    uid = f"U{random.randint(1000,9999)}"
    ct = random.choice(case_types)
    st = random.choice(sub_types)
    status = random.choices(["待处理","处理中","已完成","已关闭","待用户寄回"], weights=[20,30,30,10,10])[0]
    desc = random.choice([
        "手机收到后发现屏幕有划痕，申请换货",
        "激活后发现不喜欢，申请七天无理由退货",
        "充电时手机发热严重，怀疑质量问题",
        "快递外包装破损，手机角有磕碰",
        "购买后7天内降价，申请价保补差",
        "屏幕不慎摔碎，申请碎屏保障服务",
        "客服态度恶劣，要求投诉并赔偿",
        "收到的商品颜色与订单不符",
        "电池续航明显低于宣传，要求检测",
        "系统频繁卡顿死机，申请维修",
    ])
    ct_time = f"2026-09-{random.randint(1,3):02d} {random.randint(9,21):02d}:{random.randint(0,59):02d}"
    rt = f"2026-09-{random.randint(3,5):02d}" if status == "已完成" else ""
    res = random.choice(["同意退货退款","同意换货","免费维修","补偿优惠券50元","驳回（人为损坏）","价保补差已发放","转人工处理"]) if status == "已完成" else ""
    comp = random.choice([0,0,0,50,100,200,300]) if status == "已完成" else 0
    ws6.append([f"AS-{i:05d}", oid, uid, ct, st, desc, status, ct_time, rt, res, comp, f"客服{random.choice(['A','B','C','D'])}"])
hdr_style(ws6,12); autow(ws6)

wb.save(os.path.join(BASE,"business_data.xlsx"))
print("business_data.xlsx created with 6 sheets")

# ============================================================
# intent_taxonomy.xlsx
# ============================================================
wb2 = openpyxl.Workbook()
ws = wb2.active; ws.title="intent_taxonomy"
ws.append(["intent_id","intent","intent_cn","example_question","processing_method","requires_tool","tool_name","priority","description"])
intents = [
    ("INT001","product_spec","商品参数查询","iPhone 16 的屏幕多大？","RAG 检索商品知识卡","否","","中","查询手机具体参数，如屏幕、处理器、摄像头、电池等"),
    ("INT002","product_compare","商品对比","小米 15 和华为 Mate 70 怎么选？","RAG + 推荐逻辑","否","","高","两款或多款手机之间的参数对比和选购建议"),
    ("INT003","price_query","价格查询","iPhone 16 Pro 现在卖多少钱？","数据库/API 查询","是","query_price","高","查询商品当前售价、版本价格、优惠价"),
    ("INT004","inventory_query","库存查询","小米 15 Ultra 还有货吗？","API 查询","是","query_inventory","中","查询商品库存状态、可售数量、发货仓"),
    ("INT005","order_query","订单查询","我的订单到哪了？","API 查询","是","query_order","高","查询订单状态、物流信息、配送进度"),
    ("INT006","refund_policy","退货退款政策","激活后还能退吗？","RAG 检索政策文档","否","","中","退货、换货、退款规则咨询"),
    ("INT007","warranty_policy","保修政策","碎屏了保修吗？","RAG 检索政策文档","否","","中","保修范围、维修流程、碎屏保障咨询"),
    ("INT008","shipping_policy","配送政策","什么时候发货？","RAG 检索政策文档","否","","低","发货时间、配送范围、运费、物流异常"),
    ("INT009","promotion_query","促销活动","有什么优惠券可以用？","数据库/API 查询","是","query_promotion","中","优惠券、满减、赠品、以旧换新活动咨询"),
    ("INT010","purchase_recommend","购买推荐","预算 5000 买哪款好？","RAG + 推荐逻辑","否","","高","基于预算、用途、偏好的购机推荐"),
    ("INT011","invoice_query","发票咨询","能开发票吗？","RAG 检索政策文档","否","","低","发票类型、开具流程、重开规则"),
    ("INT012","complaint","投诉","我要投诉你们！","转人工","否","","紧急","用户投诉、不满、要求升级处理"),
    ("INT013","after_sales_apply","售后申请","手机坏了怎么修？","RAG + 工单创建","是","create_after_sales","高","提交售后申请、维修、退换货流程"),
    ("INT014","account_issue","账号问题","怎么修改收货地址？","RAG / 转人工","否","","低","账号、地址、会员相关问题"),
    ("INT015","unknown","无法识别","今天天气怎么样？","通用回复 / 转人工","否","","低","超出客服领域的问题或无法理解的意图"),
    ("INT016","greeting","问候","你好","通用回复","否","","低","打招呼、问候语"),
    ("INT017","store_info","店铺信息","你们是官方店吗？","RAG / 固定回复","否","","低","店铺资质、营业时间、联系方式"),
    ("INT018","escalation","要求人工","转人工客服","直接转人工","否","","紧急","用户明确要求人工客服"),
]
for r in intents: ws.append(r)
hdr_style(ws,9); autow(ws)
wb2.save(os.path.join(BASE,"intent_taxonomy.xlsx"))
print(f"intent_taxonomy.xlsx: {len(intents)} intents")

print("Done: business_data.xlsx, intent_taxonomy.xlsx")
