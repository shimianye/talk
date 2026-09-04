# -*- coding: utf-8 -*-
"""生成 evaluation_dataset.xlsx — 100 条客服评测问题"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import os

BASE = r"C:\Users\Administrator\Doubao\chats\2026-09-03\new-chat-5"

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

def autow(ws, mx=60):
    for col in ws.columns:
        ml=0; cl=col[0].column_letter
        for cell in col:
            if cell.value:
                v=str(cell.value); l=sum(2 if ord(c)>127 else 1 for c in v); ml=max(ml,l)
        ws.column_dimensions[cl].width=min(ml+4, mx)

wb = openpyxl.Workbook()
ws = wb.active; ws.title="evaluation"
ws.append(["id","category","question","intent","expected_answer","expected_source","should_call_tool","should_transfer_human","difficulty","evaluation_notes"])

rows = []
qid = 1

# === 30 条商品参数 ===
spec_qs = [
    ("iPhone 16 的处理器是什么？","product_spec","A18 芯片，采用第二代 3nm 工艺","kb-docs/apple/iphone-16.md","否","否","易","基础参数检索"),
    ("iPhone 16 Pro 的屏幕尺寸和刷新率是多少？","product_spec","6.3 英寸 OLED，120Hz ProMotion 自适应刷新率","kb-docs/apple/iphone-16-pro.md","否","否","易","多字段联合检索"),
    ("iPhone 15 支持无线充电吗？","product_spec","支持 MagSafe 无线充电，最高 15W","kb-docs/apple/iphone-15.md","否","否","易","充电参数"),
    ("华为 Mate 60 的电池容量和充电功率？","product_spec","4750mAh，66W 有线快充 + 50W 无线快充","kb-docs/huawei/mate-60.md","否","否","易","续航参数"),
    ("华为 Mate 70 后置摄像头配置？","product_spec","5000万主摄（可变光圈）+ 4000万超广角 + 1200万潜望长焦 + 150万多光谱","kb-docs/huawei/mate-70.md","否","否","中","多摄像头参数"),
    ("华为 Pura 70 的屏幕分辨率和刷新率？","product_spec","2760×1256，1-120Hz LTPO 自适应刷新率","kb-docs/huawei/pura-70.md","否","否","中","屏幕参数"),
    ("小米 14 的处理器和操作系统？","product_spec","骁龙 8 Gen3，小米澎湃 OS","kb-docs/xiaomi/xiaomi-14.md","否","否","易","性能参数"),
    ("小米 15 Ultra 的主摄传感器型号？","product_spec","索尼 LYT-900，1 英寸大底，f/1.63 光圈","kb-docs/xiaomi/xiaomi-15-ultra.md","否","否","难","深度参数，需精确型号"),
    ("小米 15 的重量和尺寸？","product_spec","191g，152.3×71.2×8.08mm","kb-docs/xiaomi/xiaomi-15.md","否","否","易","机身参数"),
    ("iPhone 16 有哪些颜色可选？","product_spec","黑色、白色、粉色、群青色、深青色（共5色，无沙漠色）","kb-docs/apple/iphone-16.md","否","否","中","易错点：沙漠色是Pro系列配色"),
    ("iPhone 16 Pro 的长焦是多少倍？","product_spec","5 倍光学变焦潜望长焦（120mm）","kb-docs/apple/iphone-16-pro.md","否","否","中","影像参数"),
    ("华为 Mate 60 支持卫星通信吗？","product_spec","支持北斗卫星消息","kb-docs/huawei/mate-60.md","否","否","中","特色功能"),
    ("华为 Pura 70 的防水等级？","product_spec","IP68","kb-docs/huawei/pura-70.md","否","否","易","防护参数"),
    ("小米 14 支持 NFC 吗？","product_spec","支持 NFC","kb-docs/xiaomi/xiaomi-14.md","否","否","易","连接功能"),
    ("小米 15 Ultra 支持卫星通话吗？","product_spec","支持天通卫星通话 + 北斗卫星短信","kb-docs/xiaomi/xiaomi-15-ultra.md","否","否","中","特色功能"),
    ("iPhone 16 的运行内存是多少？","product_spec","官方未公布（Apple 不公开 RAM 参数）","kb-docs/apple/iphone-16.md","否","否","中","易错点：不能用第三方传闻填充"),
    ("iPhone 15 的充电接口是什么？","product_spec","USB-C","kb-docs/apple/iphone-15.md","否","否","易","接口参数"),
    ("华为 Mate 70 的蓝牙版本？","product_spec","蓝牙 5.2，支持 LDAC 和 L2HC 高清音频","kb-docs/huawei/mate-70.md","否","否","中","连接参数"),
    ("小米 15 的 Wi-Fi 版本？","product_spec","Wi-Fi 7（802.11be）","kb-docs/xiaomi/xiaomi-15.md","否","否","中","连接参数"),
    ("iPhone 16 Pro 的 Wi-Fi 版本？","product_spec","Wi-Fi 7（802.11be）","kb-docs/apple/iphone-16-pro.md","否","否","中","连接参数，注意标准版是Wi-Fi 6E"),
    ("华为 Pura 70 的前置摄像头像素？","product_spec","1300 万像素","kb-docs/huawei/pura-70.md","否","否","易","影像参数"),
    ("小米 14 的长焦是多少倍？","product_spec","3.2 倍光学变焦（75mm）","kb-docs/xiaomi/xiaomi-14.md","否","否","中","影像参数"),
    ("iPhone 16 的电池容量是多少？","product_spec","官方未公布（Apple 不公开电池容量）","kb-docs/apple/iphone-16.md","否","否","中","易错点：不能用第三方拆解数据"),
    ("华为 Mate 60 的操作系统？","product_spec","HarmonyOS 4.0","kb-docs/huawei/mate-60.md","否","否","易","系统参数"),
    ("小米 15 Ultra 的电池容量和无线充电功率？","product_spec","6000mAh，80W 无线闪充","kb-docs/xiaomi/xiaomi-15-ultra.md","否","否","中","续航参数"),
    ("iPhone 15 的屏幕刷新率是多少？","product_spec","60Hz（不支持高刷新率）","kb-docs/apple/iphone-15.md","否","否","易","屏幕参数，易错点"),
    ("华为 Mate 70 的处理器型号？","product_spec","麒麟 9010（标准版）","kb-docs/huawei/mate-70.md","否","否","中","注意Pro版是麒麟9020"),
    ("小米 15 的浮动长焦焦距？","product_spec","60mm，2.6 倍光学变焦","kb-docs/xiaomi/xiaomi-15.md","否","否","难","深度影像参数"),
    ("iPhone 16 Pro 的机身材质？","product_spec","钛金属中框，超晶瓷面板","kb-docs/apple/iphone-16-pro.md","否","否","中","机身材质"),
    ("华为 Pura 70 支持扩展存储吗？","product_spec","不支持容量扩展（NM 存储卡需确认官方规格）","kb-docs/huawei/pura-70.md","否","否","中","存储扩展"),
]
for q in spec_qs:
    rows.append((qid,"商品参数",)+q); qid+=1

# === 20 条商品对比 ===
compare_qs = [
    ("iPhone 16 和 iPhone 16 Pro 有什么区别？","product_compare","Pro版：A18 Pro芯片、6.3英寸120Hz屏、三摄含5倍潜望长焦、钛金属机身；标准版：A18、6.1英寸60Hz屏、双摄、铝合金机身","kb-docs/apple/ + specifications表","否","否","中","同系列对比，多维度"),
    ("小米 15 和小米 15 Ultra 哪个拍照更好？","product_compare","Ultra 更好：1英寸大底主摄+2亿像素潜望长焦+全焦段覆盖；小米15为三摄但无潜望长焦","kb-docs/xiaomi/","否","否","中","影像对比"),
    ("华为 Mate 70 和 Pura 70 怎么选？","product_compare","Mate 70偏商务：麒麟9010、6.7英寸、5300mAh、卫星消息；Pura 70偏时尚影像：麒麟9000S1、6.6英寸LTPO屏、4900mAh","kb-docs/huawei/","否","否","难","跨系列对比"),
    ("iPhone 16 和小米 15 哪个更适合玩游戏？","product_compare","小米15：骁龙8至尊版、120Hz屏、5400mAh大电池、散热更好；iPhone16：A18性能强但60Hz屏、电池较小","多文档对比","否","否","难","跨品牌场景对比"),
    ("iPhone 15 和 iPhone 16 升级了什么？","product_compare","iPhone 16升级：A18芯片（A16→A18）、相机控制按钮、操作按钮、新增群青色/深青色、Apple Intelligence支持","kb-docs/apple/","否","否","中","代际对比"),
    ("华为 Mate 60 和 Mate 70 的区别？","product_compare","Mate70升级：麒麟9010（9000S→9010）、5300mAh电池（4750→5300）、红枫原色影像、星闪、HarmonyOS 4.3","kb-docs/huawei/","否","否","中","代际对比"),
    ("小米 14 和小米 15 哪个性价比高？","product_compare","小米14首发3999起，骁龙8Gen3；小米15首发4499起，骁龙8至尊版、5400mAh大电池。预算有限选14，追求最新性能选15","kb-docs/xiaomi/","否","否","中","性价比对比"),
    ("iPhone 16 Pro 和小米 15 Ultra 影像对比？","product_compare","iPhone16Pro：4800万三摄+5倍潜望，视频能力强；小米15Ultra：1英寸大底+2亿潜望，硬件参数更强，徕卡色彩","多文档对比","否","否","难","旗舰影像对比"),
    ("华为 Pura 70 和小米 15 哪个屏幕好？","product_compare","小米15：6.36英寸2670×1200，120Hz，3200nit；Pura70：6.6英寸2760×1256，LTPO 1-120Hz，2500nit。Pura70有LTPO更省电","kb-docs/","否","否","难","屏幕参数对比"),
    ("iPhone 16 和华为 Pura 70 怎么选？","product_compare","iPhone16：iOS生态、A18、视频录制强；Pura70：鸿蒙生态、可变光圈主摄、信号好、快充更强。看生态偏好","多文档对比","否","否","难","跨品牌综合对比"),
    ("小米 15 Ultra 和 iPhone 16 Pro Max 哪个续航好？","product_compare","小米15Ultra：6000mAh+90W有线+80W无线；iPhone16ProMax电池官方未公布但续航为iPhone系列最强。小米电池容量更大","多文档对比","否","否","中","续航对比，注意Apple不公布电池"),
    ("华为 Mate 70 和小米 15 性能对比？","product_compare","小米15骁龙8至尊版性能更强；Mate70麒麟9010日常够用，通信和卫星功能更强","多文档对比","否","否","中","性能对比"),
    ("iPhone 15 和华为 Mate 60 哪个更值得买？","product_compare","iPhone15：iOS生态、A16、4800万主摄；Mate60：麒麟9000S、卫星消息、66W快充、信号更强。看生态和功能需求","多文档对比","否","否","难","跨品牌综合"),
    ("小米 14 和 iPhone 16 尺寸对比？","product_compare","小米14：6.36英寸，152.8×71.5×8.20mm，193g；iPhone16：6.1英寸，147.6×71.6×7.8mm，170g。iPhone更轻薄","kb-docs/","否","否","易","尺寸对比"),
    ("华为 Pura 70 和 Mate 60 影像对比？","product_compare","Pura70：5000万超聚光主摄+1300万超广角（双摄）；Mate60：5000万超光变+1200万超广角+1200万潜望长焦（三摄）。Mate60焦段更全","kb-docs/huawei/","否","否","中","影像对比"),
    ("iPhone 16 Pro 和华为 Mate 70 Pro+ 哪个信号好？","product_compare","华为通信能力传统优势，Mate70系列支持灵犀通信、卫星消息；iPhone信号表现一般。华为更优","多文档对比","否","否","中","通信对比"),
    ("小米 15 和 iPhone 16 充电对比？","product_compare","小米15：90W有线+50W无线；iPhone16：20W有线+15W MagSafe无线。小米充电快很多","kb-docs/","否","否","易","充电对比"),
    ("iPhone 16 Pro 和小米 15 Ultra 价格对比？","product_compare","iPhone16Pro 7999起；小米15Ultra 6499起。同存储版本小米便宜约1500元","variants表","否","否","易","价格对比"),
    ("华为 Mate 60 和 Pura 70 哪个更轻薄？","product_compare","Pura70：207g，157.6×74.3×7.95mm；Mate60：209g，161.4×76×7.95mm。Pura70略轻薄","kb-docs/huawei/","否","否","易","机身对比"),
    ("三款小屏旗舰（iPhone16/小米15/华为Pura70）怎么选？","product_compare","iPhone16：iOS生态、最轻薄；小米15：性能最强、充电最快；Pura70：鸿蒙生态、LTPO屏、信号好。按生态和需求选","多文档对比","否","否","难","三机综合对比"),
]
for q in compare_qs:
    rows.append((qid,"商品对比",)+q); qid+=1

# === 15 条购买推荐 ===
recommend_qs = [
    ("预算 5000 元，应该选哪款手机？","purchase_recommend","推荐小米15（4499起）或华为Pura70（5499起，活动价可能更低）。iPhone16 5999起略超预算。小米15性能和充电最强","多文档+variants","否","否","中","预算推荐"),
    ("主要用来拍照，哪款手机最好？","purchase_recommend","小米15 Ultra（1英寸大底+2亿潜望+徕卡），其次iPhone16 Pro（视频能力强），华为Mate70 Pro+（红枫原色）","kb-docs/","否","否","中","影像推荐"),
    ("哪款手机最适合玩大型游戏？","purchase_recommend","小米15（骁龙8至尊版+120Hz+5400mAh+翼型环冷散热），其次小米15 Ultra。iPhone16 Pro性能强但散热一般","多文档","否","否","中","游戏推荐"),
    ("经常出差，需要长续航和信号好，选哪款？","purchase_recommend","华为Mate70（5300mAh+灵犀通信+卫星消息），或小米15 Ultra（6000mAh+卫星通信）","kb-docs/","否","否","中","续航信号推荐"),
    ("女生用，喜欢轻薄好看的，推荐哪款？","purchase_recommend","iPhone16（170g最轻薄，粉色/群青色好看），或华为Pura70（樱玫红/薰衣草紫，207g）","kb-docs/","否","否","易","外观推荐"),
    ("想体验 iOS 生态，买 iPhone 15 还是 16？","purchase_recommend","预算充足选iPhone16（A18+Apple Intelligence+相机按钮）；预算有限iPhone15性价比更高，核心体验差距不大","kb-docs/apple/","否","否","中","iOS选购"),
    ("华为用户，Mate 60 还值得买吗？还是等新机？","purchase_recommend","Mate60已降价，性价比不错；但Mate70性能和续航更好。预算够选Mate70，追求性价比Mate60仍可买","kb-docs/huawei/","否","否","中","选购建议"),
    ("小米 14 和 15 买哪个？","purchase_recommend","小米15升级骁龙8至尊版+5400mAh大电池，加200元值得；预算紧小米14降价后性价比高","kb-docs/xiaomi/","否","否","易","同系列选购"),
    ("需要卫星通信功能，哪几款支持？","purchase_recommend","华为Mate60/Mate70（北斗卫星消息）、小米15 Ultra（天通卫星通话+北斗短信）。iPhone系列中国大陆版不支持卫星通信","多文档","否","否","中","功能筛选"),
    ("想要无线充电快的手机，推荐哪款？","purchase_recommend","小米15 Ultra（80W无线闪充最快），其次小米14/15（50W），华为Mate70/Pura70（50W），iPhone系列15W MagSafe","多文档","否","否","中","充电推荐"),
    ("预算 8000 元，买顶配还是旗舰标准版？","purchase_recommend","可买iPhone16 Pro 256GB（8999，略超）或小米15 Ultra 16GB+1TB（7799）。小米配置更高，苹果生态体验好","variants+多文档","否","否","难","高端选购"),
    ("给父母买手机，哪款合适？","purchase_recommend","华为Mate70或Pura70（鸿蒙系统简易模式、信号好、续航长），或小米15（大字体模式、性价比高）","多文档","否","否","中","人群推荐"),
    ("喜欢拍视频，iPhone 16 和 16 Pro 选哪个？","purchase_recommend","iPhone16 Pro（4800万三摄+ProRes视频+5倍长焦），视频创作能力明显强于标准版","kb-docs/apple/","否","否","中","视频推荐"),
    ("哪款手机支持 IP68 防水？","purchase_recommend","全部9款均支持IP68防水。注意：防水不代表可在水中使用，进水不在保修范围","specifications表","否","否","易","功能筛选"),
    ("想要小屏手机，有哪些选择？","purchase_recommend","iPhone16（6.1英寸/170g）、小米14/15（6.36英寸）。华为机型均在6.6英寸以上，不算小屏","多文档","否","否","中","尺寸筛选"),
]
for q in recommend_qs:
    rows.append((qid,"购买推荐",)+q); qid+=1

# === 15 条售后政策 ===
policy_qs = [
    ("手机激活后还能七天无理由退货吗？","refund_policy","不能。手机一经激活不适用七天无理由退货，除非存在非人为质量问题","policies/return-and-refund.md","否","否","易","退货规则"),
    ("屏幕摔碎了，保修吗？","warranty_policy","人为摔碎不在免费保修范围。如购买了碎屏保障服务，可享受1次免费换屏；否则需付费维修","policies/warranty.md","否","否","中","保修范围"),
    ("发货后多久能收到？","shipping_policy","中国大陆1-3个工作日，偏远地区3-7个工作日。手机默认顺丰或京东物流","policies/shipping.md","否","否","易","配送时效"),
    ("可以开发票吗？怎么开？","invoice_query","可以，提供增值税电子普通发票。下单时勾选或收货后30天内联系客服，需提供抬头和税号","policies/invoice.md","否","否","易","发票规则"),
    ("优惠券可以叠加使用吗？","promotion_query","同一订单最多使用1张店铺优惠券，可与店铺满减叠加，不可与平台券叠加","policies/promotion-rules.md","否","否","中","促销规则"),
    ("退货时赠品要一起寄回吗？","refund_policy","需要。赠品需一并退回，遗失或损坏按市场价从退款中扣除","policies/return-and-refund.md","否","否","易","退货细节"),
    ("保修期是多久？","warranty_policy","主机12个月，充电器/数据线12个月，电池12个月（容量低于80%可检测），赠品配件3个月","policies/warranty.md","否","否","易","保修期限"),
    ("快递到了发现包装破损怎么办？","shipping_policy","请当场拒收并立即联系客服。如已签收后发现破损，需提供开箱视频和快递凭证核实处理","policies/shipping.md","否","否","中","物流异常"),
    ("买贵了可以退差价吗？","promotion_query","签收7天内商品降价（不含秒杀/拼团价）可申请价保，以优惠券形式返还","policies/promotion-rules.md","否","否","中","价保规则"),
    ("手机进水了能免费修吗？","warranty_policy","不能。进液属于人为损坏，不在免费保修范围，需付费维修。IP68防护不保证可在水中使用","policies/warranty.md","否","否","中","进水保修"),
    ("退款多久能到账？","refund_policy","支付宝/微信1-3个工作日，银行卡3-7个工作日，花呗/信用卡分期以银行处理时效为准","policies/return-and-refund.md","否","否","易","退款时效"),
    ("以旧换新怎么操作？","promotion_query","购机时选择以旧换新，旧机由合作回收平台估价，最终价以实际检测为准。旧机寄出前请备份数据并退出账号","policies/promotion-rules.md","否","否","中","以旧换新"),
    ("充电器坏了可以换吗？","warranty_policy","原装充电器保修期12个月，非人为损坏可免费更换。需提供购买凭证","policies/warranty.md","否","否","易","配件保修"),
    ("秒杀商品可以退货吗？","refund_policy","秒杀商品不支持七天无理由退货（质量问题除外），且不参与其他优惠叠加","policies/promotion-rules.md","否","否","中","秒杀规则"),
    ("发票开错了能重开吗？","invoice_query","开具后30天内可申请重开，需提供原发票号码和正确信息。已报销/入账的不支持重开","policies/invoice.md","否","否","中","发票重开"),
]
for q in policy_qs:
    rows.append((qid,"售后政策",)+q); qid+=1

# === 10 条订单/物流 ===
order_qs = [
    ("我的订单 ORD202609001 到哪了？","order_query","需调用订单和物流API查询实时状态","business_data/orders+logistics","是","否","中","需工具调用"),
    ("我昨天买的手机发货了吗？","order_query","需调用订单API查询订单状态，已发货则返回物流单号","business_data/orders","是","否","中","需工具调用"),
    ("订单显示已签收但我没收到货怎么办？","order_query","联系客服核实，需提供订单号。可能为代收点签收或快递异常，客服将联系快递方处理","policies/shipping.md","否","是","中","物流异常，可能转人工"),
    ("怎么修改收货地址？","order_query","未发货前可免费修改；已发货无法修改，需退回重发并承担运费。联系客服处理","policies/shipping.md","否","否","易","地址修改"),
    ("我买的小米15有库存吗，什么时候能发？","inventory_query","需调用库存API查询可售数量和仓库","business_data/inventory","是","否","中","需工具调用"),
    ("订单取消了优惠券会退吗？","refund_policy","整单取消且优惠券在有效期内会退回；部分退款优惠券不退回。过期作废","policies/promotion-rules.md","否","否","中","优惠券退回"),
    ("物流三天没更新了正常吗？","order_query","不正常，可能为物流中转延迟或异常。联系客服催件，超过48小时未更新可申请核查","policies/shipping.md","否","否","中","物流异常"),
    ("我想查一下 ORD202609015 的退款进度","order_query","需调用订单/售后API查询退款状态","business_data/orders+after_sales","是","否","中","需工具调用"),
    ("买了两台手机，可以分开配送吗？","shipping_policy","同一订单默认一个包裹发货。如需分开配送请在下单前联系客服，可能产生额外运费","policies/shipping.md","否","否","中","配送方式"),
    ("快递被退回了怎么办？","shipping_policy","因地址错误/无人签收导致退回的，用户承担往返运费，核实后可重新发货或退款","policies/shipping.md","否","否","中","退回处理"),
]
for q in order_qs:
    rows.append((qid,"订单物流",)+q); qid+=1

# === 10 条越权/投诉/无答案 ===
edge_qs = [
    ("你们老板电话是多少？我要直接投诉","complaint","正在为您转接人工客服，请稍候。我们会认真处理您的问题","policies/customer-service-escalation.md","否","是","难","必须转人工，不得编造老板电话"),
    ("我要告你们，等着收律师函吧","complaint","非常抱歉给您带来不好的体验，正在为您转接高级客服专员处理","policies/customer-service-escalation.md","否","是","难","情绪激动+法律威胁，转人工"),
    ("能帮我查一下别人的订单信息吗？","unknown","抱歉，我无法查询他人订单信息，这涉及用户隐私。请使用下单账号查询","—","否","否","中","隐私保护，拒绝越权"),
    ("你们这个手机能跑多少分？安兔兔跑分多少？","unknown","官方未公布跑分数据，建议参考专业评测机构的实测数据。我可以提供官方性能参数","—","否","否","中","无官方数据，不编造"),
    ("这款手机用的是哪家屏幕供应商？","unknown","官方未公布屏幕供应商具体信息，建议以官方参数页为准。我可以提供屏幕类型和参数","—","否","否","中","供应链信息不公开"),
    ("我要投诉客服态度差，怎么处理？","complaint","非常抱歉，正在为您转接客服主管处理。请稍候，我们会认真对待您的反馈","policies/customer-service-escalation.md","否","是","易","投诉转人工"),
    ("你们和某某品牌是什么关系？是不是山寨店？","store_info","本店为正规授权经销商，所售商品均为正品，享受品牌官方保修。可提供授权资质查询","—","否","否","中","店铺资质"),
    ("能便宜点吗？给我个内部价","unknown","商品价格以页面为准，可关注优惠券和促销活动。我无法提供内部折扣价","—","否","否","易","拒绝违规议价"),
    ("手机爆炸了，我要你们赔偿！","complaint","非常抱歉出现这种情况，请您先确保人身安全。正在为您紧急转接专人处理，我们会全力配合调查和赔偿","policies/customer-service-escalation.md","否","是","难","安全事故，紧急转人工"),
    ("你是谁？你是真人吗？","greeting","我是智能客服助手，可以帮您查询商品参数、订单物流、售后政策等。需要人工服务请说'转人工'","—","否","否","易","身份确认"),
]
for q in edge_qs:
    rows.append((qid,"边界与投诉",)+q); qid+=1

for r in rows:
    ws.append(r)
hdr_style(ws,10); autow(ws)

# stats sheet
ws2 = wb.create_sheet("stats")
ws2.append(["指标","数值","说明"])
ws2.append(["总问题数",len(rows),""])
cats = {}
for r in rows:
    cats[r[1]] = cats.get(r[1],0)+1
for k,v in cats.items():
    ws2.append([k,v,""])
ws2.append(["","",""])
ws2.append(["评测维度","",""])
ws2.append(["Recall@5","待评测","检索返回Top5包含正确答案的比例"])
ws2.append(["答案准确率","待评测","答案与expected_answer一致的比例"])
ws2.append(["引用正确率","待评测","引用来源与expected_source匹配的比例"])
ws2.append(["工具调用准确率","待评测","should_call_tool与实际调用一致的比例"])
ws2.append(["转人工准确率","待评测","should_transfer_human与实际转人工一致的比例"])
ws2.append(["幻觉率","待评测","编造不存在信息的比例"])
ws2.append(["平均响应时间","待评测","毫秒级"])
hdr_style(ws2,3); autow(ws2)

wb.save(os.path.join(BASE,"evaluation_dataset.xlsx"))
print(f"evaluation_dataset.xlsx: {len(rows)} questions")
print(f"Categories: {cats}")
