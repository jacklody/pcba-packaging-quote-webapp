export const LOGISTICS_PRODUCTS = ["特惠普运", "次日达"];

export const PACKAGING_MODE_OPTIONS = [
  { value: "auto", label: "自动判断（推荐）" },
  { value: "divider", label: "小板刀卡隔档包装" },
  { value: "foam", label: "大板 EPE/EPS 成型缓冲包装" },
];

export const STRUCTURE_FEATURE_FIELDS = [
  { key: "has_heat_sink", label: "有铝散热器", help: "仅作为结构风险提示；实际尺寸变化请在外扩尺寸中录入。", allowanceHelp: "录入散热器导致的长/宽/高最大外扩。" },
  { key: "has_sheet_metal", label: "有结构钣金", help: "仅作为结构风险提示；实际尺寸变化请在外扩尺寸中录入。", allowanceHelp: "录入钣金折边、支架或防磕碰需要增加的包络。" },
  { key: "has_wire_harness", label: "有线束/附件同箱", help: "仅作为结构风险提示；实际尺寸变化请在外扩尺寸中录入。", allowanceHelp: "录入线束弯折半径、接插件和附件隔舱占位。" },
  { key: "has_tall_fragile_components", label: "有高大/易损器件", help: "仅作为结构风险提示；实际尺寸变化请在外扩尺寸中录入。", allowanceHelp: "录入大电容、电感、变压器等顶部保护余量。" },
];

export const SUPPORTED_3D_FILE_EXTENSIONS = [".step", ".stp", ".iges", ".igs", ".stl", ".obj", ".glb", ".gltf", ".png", ".jpg", ".jpeg"];

export const STANDARD_CARTONS = [
  { carton_id: "STD-01", length_mm: 300, width_mm: 250, height_mm: 180, modularity: "✅", typical_use: "小板、电源小板、样品箱", source: "standard", enabled: true },
  { carton_id: "STD-02", length_mm: 350, width_mm: 300, height_mm: 200, modularity: "✅", typical_use: "中小控制器板，小号ESD箱", source: "standard", enabled: true },
  { carton_id: "STD-03", length_mm: 400, width_mm: 300, height_mm: 220, modularity: "✅", typical_use: "A5‑A4尺寸PCBA，多SKU小批量", source: "standard", enabled: true },
  { carton_id: "STD-04", length_mm: 400, width_mm: 300, height_mm: 260, modularity: "✅", typical_use: "A5‑A4尺寸PCBA，容量加大", source: "standard", enabled: true },
  { carton_id: "STD-05", length_mm: 450, width_mm: 350, height_mm: 230, modularity: "✅", typical_use: "行业通用，家电控制板主力中小批量", source: "standard", enabled: true },
  { carton_id: "STD-06", length_mm: 450, width_mm: 350, height_mm: 280, modularity: "✅", typical_use: "家电控制板，加高版，高元件注意隔板", source: "standard", enabled: true },
  { carton_id: "STD-07", length_mm: 500, width_mm: 400, height_mm: 240, modularity: "✅✅", typical_use: "黄金优选，大批量家电/商空PCBA", source: "standard", enabled: true },
  { carton_id: "STD-08", length_mm: 500, width_mm: 400, height_mm: 280, modularity: "✅✅", typical_use: "液冷泵、变频板大批量出货", source: "standard", enabled: true },
  { carton_id: "STD-09", length_mm: 500, width_mm: 400, height_mm: 320, modularity: "✅✅", typical_use: "大容量，连接器多板慎用，注意堆码总高", source: "standard", enabled: true },
  { carton_id: "STD-10", length_mm: 530, width_mm: 380, height_mm: 260, modularity: "⚠️", typical_use: "海尔系供应商常用，大板拼板，托盘利用率一般", source: "standard", enabled: true },
  { carton_id: "STD-11", length_mm: 530, width_mm: 380, height_mm: 300, modularity: "⚠️", typical_use: "空调主控大板", source: "standard", enabled: true },
  { carton_id: "STD-12", length_mm: 550, width_mm: 400, height_mm: 260, modularity: "⚠️", typical_use: "大板多拼板，空隙略大", source: "standard", enabled: true },
  { carton_id: "STD-13", length_mm: 580, width_mm: 420, height_mm: 300, modularity: "⚠️", typical_use: "超大PCBA，优先评估托盘利用率", source: "standard", enabled: true },
  { carton_id: "STD-14", length_mm: 600, width_mm: 400, height_mm: 250, modularity: "✅✅", typical_use: "模数基准，适合超大板，纸箱单价偏高", source: "standard", enabled: true },
  { carton_id: "STD-15", length_mm: 600, width_mm: 400, height_mm: 300, modularity: "✅✅", typical_use: "纸质ESD箱上限，偏重建议改用中空周转箱", source: "standard", enabled: true },
];

export const DESTINATIONS = ["福州市", "厦门市", "泉州市", "宁德市", "莆田市", "漳州市", "龙岩市", "三明市", "南平市", "拉萨市", "日喀则市", "山南市", "林芝市", "昌都市", "那曲市", "阿里地区", "贵阳市", "遵义市", "安顺市", "黔南布依族苗族自治州", "黔东南苗族侗族自治州", "铜仁市", "毕节市", "六盘水市", "黔西南布依族苗族自治州", "广州市", "深圳市", "珠海市", "中山市", "东莞市", "江门市", "惠州市", "佛山市", "肇庆市", "汕尾市", "阳江市", "揭阳市", "茂名市", "韶关市", "梅州市", "汕头市", "湛江市", "河源市", "清远市", "云浮市", "潮州市", "武汉市", "鄂州市", "襄阳市", "孝感市", "黄石市", "荆州市", "宜昌市", "神农架林区", "十堰市", "随州市", "荆门市", "黄冈市", "咸宁市", "恩施土家族苗族自治州", "潜江市", "仙桃市", "天门市", "株洲市", "长沙市", "湘潭市", "益阳市", "岳阳市", "衡阳市", "郴州市", "常德市", "娄底市", "邵阳市", "湘西土家族苗族自治州", "张家界市", "怀化市", "永州市", "重庆市", "成都市", "资阳市", "眉山市", "绵阳市", "自贡市", "南充市", "达州市", "遂宁市", "广安市", "巴中市", "泸州市", "宜宾市", "内江市", "乐山市", "雅安市", "德阳市", "广元市", "攀枝花市", "凉山彝族自治州", "甘孜藏族自治州", "阿坝藏族羌族自治州", "合肥市", "芜湖市", "马鞍山市", "滁州市", "蚌埠市", "六安市", "淮南市", "安庆市", "宿州市", "亳州市", "阜阳市", "黄山市", "淮北市", "铜陵市", "宣城市", "池州市", "乌鲁木齐市", "塔城地区", "白杨市", "新星市", "哈密市", "昆玉市", "和田地区", "北屯市", "阿勒泰地区", "克孜勒苏柯尔克孜自治州", "双河市", "博尔塔拉蒙古自治州", "克拉玛依市", "胡杨河市", "石河子市", "五家渠市", "昌吉回族自治州", "吐鲁番市", "巴音郭楞蒙古自治州", "铁门关市", "阿克苏地区", "阿拉尔市", "图木舒克市", "喀什地区", "伊犁哈萨克自治州", "可克达拉市", "南京市", "无锡市", "苏州市", "常州市", "镇江市", "南通市", "扬州市", "盐城市", "徐州市", "淮安市", "连云港市", "泰州市", "宿迁市", "天津市", "长春市", "吉林市", "延边朝鲜族自治州", "四平市", "通化市", "白城市", "辽源市", "松原市", "白山市", "银川市", "石嘴山市", "吴忠市", "固原市", "中卫市", "石家庄市", "廊坊市", "邯郸市", "保定市", "雄安新区", "唐山市", "沧州市", "秦皇岛市", "张家口市", "承德市", "衡水市", "邢台市", "开封市", "郑州市", "新乡市", "许昌市", "信阳市", "洛阳市", "鹤壁市", "商丘市", "安阳市", "平顶山市", "南阳市", "焦作市", "济源市", "濮阳市", "周口市", "漯河市", "驻马店市", "三门峡市", "崇左市", "南宁市", "柳州市", "来宾市", "桂林市", "防城港市", "梧州市", "贺州市", "贵港市", "玉林市", "百色市", "钦州市", "河池市", "北海市", "屯昌县", "五指山市", "白沙黎族自治县", "东方市", "保亭黎族苗族自治县", "琼中黎族苗族自治县", "定安县", "临高县", "陵水黎族自治县", "文昌市", "海口市", "万宁市", "乐东黎族自治县", "琼海市", "澄迈县", "昌江黎族自治县", "儋州市", "三亚市", "三沙市", "上海市", "南昌市", "九江市", "吉安市", "赣州市", "鹰潭市", "新余市", "上饶市", "抚州市", "宜春市", "景德镇市", "萍乡市", "昆明市", "大理白族自治州", "曲靖市", "玉溪市", "楚雄彝族自治州", "西双版纳傣族自治州", "德宏傣族景颇族自治州", "昭通市", "红河哈尼族彝族自治州", "保山市", "文山壮族苗族自治州", "普洱市", "临沧市", "怒江傈僳族自治州", "迪庆藏族自治州", "丽江市", "兰州市", "临夏回族自治州", "定西市", "平凉市", "庆阳市", "金昌市", "武威市", "张掖市", "嘉峪关市", "酒泉市", "天水市", "陇南市", "甘南藏族自治州", "白银市", "西安市", "咸阳市", "宝鸡市", "铜川市", "延安市", "榆林市", "渭南市", "商洛市", "安康市", "汉中市", "杭州市", "嘉兴市", "宁波市", "湖州市", "绍兴市", "金华市", "台州市", "温州市", "衢州市", "丽水市", "舟山市", "呼和浩特市", "包头市", "呼伦贝尔市", "乌海市", "乌兰察布市", "通辽市", "赤峰市", "鄂尔多斯市", "巴彦淖尔市", "锡林郭勒盟", "兴安盟", "阿拉善盟", "西宁市", "海北藏族自治州", "海东市", "黄南藏族自治州", "海南藏族自治州", "果洛藏族自治州", "玉树藏族自治州", "海西蒙古族藏族自治州", "抚顺市", "本溪市", "铁岭市", "沈阳市", "大连市", "鞍山市", "丹东市", "锦州市", "营口市", "阜新市", "辽阳市", "朝阳市", "盘锦市", "葫芦岛市", "哈尔滨市", "齐齐哈尔市", "牡丹江市", "佳木斯市", "绥化市", "黑河市", "大兴安岭地区", "伊春市", "大庆市", "七台河市", "鸡西市", "鹤岗市", "双鸭山市", "北京市", "太原市", "晋中市", "朔州市", "忻州市", "大同市", "阳泉市", "长治市", "晋城市", "临汾市", "吕梁市", "运城市"];

export const DESTINATION_GROUPS = [
  { province: "北京", destinations: ["北京市"] },
  { province: "上海", destinations: ["上海市"] },
  { province: "天津", destinations: ["天津市"] },
  { province: "重庆", destinations: ["重庆市"] },
  { province: "江苏省", destinations: ["南京市", "无锡市", "苏州市", "常州市", "镇江市", "南通市", "扬州市", "盐城市", "徐州市", "淮安市", "连云港市", "泰州市", "宿迁市"] },
  { province: "浙江省", destinations: ["杭州市", "嘉兴市", "宁波市", "湖州市", "绍兴市", "金华市", "台州市", "温州市", "衢州市", "丽水市", "舟山市"] },
  { province: "安徽省", destinations: ["合肥市", "芜湖市", "马鞍山市", "滁州市", "蚌埠市", "六安市", "淮南市", "安庆市", "宿州市", "亳州市", "阜阳市", "黄山市", "淮北市", "铜陵市", "宣城市", "池州市"] },
  { province: "福建省", destinations: ["福州市", "厦门市", "泉州市", "宁德市", "莆田市", "漳州市", "龙岩市", "三明市", "南平市"] },
  { province: "江西省", destinations: ["南昌市", "九江市", "吉安市", "赣州市", "鹰潭市", "新余市", "上饶市", "抚州市", "宜春市", "景德镇市", "萍乡市"] },
  { province: "广东省", destinations: ["广州市", "深圳市", "珠海市", "中山市", "东莞市", "江门市", "惠州市", "佛山市", "肇庆市", "汕尾市", "阳江市", "揭阳市", "茂名市", "韶关市", "梅州市", "汕头市", "湛江市", "河源市", "清远市", "云浮市", "潮州市"] },
  { province: "广西壮族自治区", destinations: ["崇左市", "南宁市", "柳州市", "来宾市", "桂林市", "防城港市", "梧州市", "贺州市", "贵港市", "玉林市", "百色市", "钦州市", "河池市", "北海市"] },
  { province: "海南省", destinations: ["屯昌县", "五指山市", "白沙黎族自治县", "东方市", "保亭黎族苗族自治县", "琼中黎族苗族自治县", "定安县", "临高县", "陵水黎族自治县", "文昌市", "海口市", "万宁市", "乐东黎族自治县", "琼海市", "澄迈县", "昌江黎族自治县", "儋州市", "三亚市", "三沙市"] },
  { province: "河南省", destinations: ["开封市", "郑州市", "新乡市", "许昌市", "信阳市", "洛阳市", "鹤壁市", "商丘市", "安阳市", "平顶山市", "南阳市", "焦作市", "济源市", "濮阳市", "周口市", "漯河市", "驻马店市", "三门峡市"] },
  { province: "湖北省", destinations: ["武汉市", "鄂州市", "襄阳市", "孝感市", "黄石市", "荆州市", "宜昌市", "神农架林区", "十堰市", "随州市", "荆门市", "黄冈市", "咸宁市", "恩施土家族苗族自治州", "潜江市", "仙桃市", "天门市"] },
  { province: "湖南省", destinations: ["株洲市", "长沙市", "湘潭市", "益阳市", "岳阳市", "衡阳市", "郴州市", "常德市", "娄底市", "邵阳市", "湘西土家族苗族自治州", "张家界市", "怀化市", "永州市"] },
  { province: "河北省", destinations: ["石家庄市", "廊坊市", "邯郸市", "保定市", "雄安新区", "唐山市", "沧州市", "秦皇岛市", "张家口市", "承德市", "衡水市", "邢台市"] },
  { province: "山西省", destinations: ["太原市", "晋中市", "朔州市", "忻州市", "大同市", "阳泉市", "长治市", "晋城市", "临汾市", "吕梁市", "运城市"] },
  { province: "内蒙古自治区", destinations: ["呼和浩特市", "包头市", "呼伦贝尔市", "乌海市", "乌兰察布市", "通辽市", "赤峰市", "鄂尔多斯市", "巴彦淖尔市", "锡林郭勒盟", "兴安盟", "阿拉善盟"] },
  { province: "陕西省", destinations: ["西安市", "咸阳市", "宝鸡市", "铜川市", "延安市", "榆林市", "渭南市", "商洛市", "安康市", "汉中市"] },
  { province: "甘肃省", destinations: ["兰州市", "临夏回族自治州", "定西市", "平凉市", "庆阳市", "金昌市", "武威市", "张掖市", "嘉峪关市", "酒泉市", "天水市", "陇南市", "甘南藏族自治州", "白银市"] },
  { province: "宁夏回族自治区", destinations: ["银川市", "石嘴山市", "吴忠市", "固原市", "中卫市"] },
  { province: "青海省", destinations: ["西宁市", "海北藏族自治州", "海东市", "黄南藏族自治州", "海南藏族自治州", "果洛藏族自治州", "玉树藏族自治州", "海西蒙古族藏族自治州"] },
  { province: "新疆维吾尔自治区", destinations: ["乌鲁木齐市", "塔城地区", "白杨市", "新星市", "哈密市", "昆玉市", "和田地区", "北屯市", "阿勒泰地区", "克孜勒苏柯尔克孜自治州", "双河市", "博尔塔拉蒙古自治州", "克拉玛依市", "胡杨河市", "石河子市", "五家渠市", "昌吉回族自治州", "吐鲁番市", "巴音郭楞蒙古自治州", "铁门关市", "阿克苏地区", "阿拉尔市", "图木舒克市", "喀什地区", "伊犁哈萨克自治州", "可克达拉市"] },
  { province: "四川省", destinations: ["成都市", "资阳市", "眉山市", "绵阳市", "自贡市", "南充市", "达州市", "遂宁市", "广安市", "巴中市", "泸州市", "宜宾市", "内江市", "乐山市", "雅安市", "德阳市", "广元市", "攀枝花市", "凉山彝族自治州", "甘孜藏族自治州", "阿坝藏族羌族自治州"] },
  { province: "贵州省", destinations: ["贵阳市", "遵义市", "安顺市", "黔南布依族苗族自治州", "黔东南苗族侗族自治州", "铜仁市", "毕节市", "六盘水市", "黔西南布依族苗族自治州"] },
  { province: "云南省", destinations: ["昆明市", "大理白族自治州", "曲靖市", "玉溪市", "楚雄彝族自治州", "西双版纳傣族自治州", "德宏傣族景颇族自治州", "昭通市", "红河哈尼族彝族自治州", "保山市", "文山壮族苗族自治州", "普洱市", "临沧市", "怒江傈僳族自治州", "迪庆藏族自治州", "丽江市"] },
  { province: "西藏自治区", destinations: ["拉萨市", "日喀则市", "山南市", "林芝市", "昌都市", "那曲市", "阿里地区"] },
  { province: "辽宁省", destinations: ["抚顺市", "本溪市", "铁岭市", "沈阳市", "大连市", "鞍山市", "丹东市", "锦州市", "营口市", "阜新市", "辽阳市", "朝阳市", "盘锦市", "葫芦岛市"] },
  { province: "吉林省", destinations: ["长春市", "吉林市", "延边朝鲜族自治州", "四平市", "通化市", "白城市", "辽源市", "松原市", "白山市"] },
  { province: "黑龙江省", destinations: ["哈尔滨市", "齐齐哈尔市", "牡丹江市", "佳木斯市", "绥化市", "黑河市", "大兴安岭地区", "伊春市", "大庆市", "七台河市", "鸡西市", "鹤岗市", "双鸭山市"] },
];

export const ORIGINS = ["青岛市", ...DESTINATIONS];
export const ORIGIN_GROUPS = [{ province: "山东省", destinations: ["青岛市"] }, ...DESTINATION_GROUPS];

export const PALLET_AUTO_OPTION = { value: "auto", label: "自动选托盘（枚举标准托盘）" };

export const PALLET_PRESETS = [
  { value: "1100x1100", label: "1100×1100 木托盘", material: "wood", height_mm: 120, max_weight_kg: 700, reusable: false },
  { value: "1200x1000", label: "1200×1000 木托盘", material: "wood", height_mm: 140, max_weight_kg: 900, reusable: false },
  { value: "1200x800", label: "1200×800 木托盘", material: "wood", height_mm: 140, max_weight_kg: 700, reusable: false },
  { value: "1140x1140", label: "1140×1140 木托盘", material: "wood", height_mm: 140, max_weight_kg: 900, reusable: false },
  { value: "1219x1016", label: "1219×1016 木托盘", material: "wood", height_mm: 140, max_weight_kg: 1000, reusable: false },
];

export const CARTON_PRESETS = [
  { value: "5-BC", label: "5层 BC 楞（默认）", layers: 5, flute: "BC", thickness_mm: 7, max_load_kg: 35, stack_safety_factor: 1.5 },
  { value: "5-C", label: "5层 C 楞", layers: 5, flute: "C", thickness_mm: 6, max_load_kg: 28, stack_safety_factor: 1.5 },
  { value: "7-BC", label: "7层 BC 楞加强", layers: 7, flute: "BC", thickness_mm: 10, max_load_kg: 55, stack_safety_factor: 1.8 },
];

export function getPalletPreset(value) {
  if (value === "auto") return null;
  return PALLET_PRESETS.find((p) => p.value === value) || PALLET_PRESETS[0];
}

export function getCartonPreset(value) {
  return CARTON_PRESETS.find((p) => p.value === value) || CARTON_PRESETS[0];
}

export const COST_FIELDS = [
  { key: "eps_base_fee", label: "EPS 基础费", unit: "元/m²", default: 60, low: 40, typical: 60, high: 90, grade: "B" },
  { key: "eps_vol_fee", label: "EPS 体积费", unit: "元/m³", default: 520, low: 350, typical: 520, high: 700, grade: "B" },
  { key: "epe_unit_price_per_m3", label: "EPE 单价", unit: "元/m³", default: 650, low: 450, typical: 650, high: 1200, grade: "B" },
  {
    key: "corrugated_material_yuan_per_m2",
    label: "纸箱材料单价",
    unit: "元/m²",
    default: 14.35,
    low: 8,
    typical: 14.35,
    high: 22,
    grade: "A",
    help: "默认按面积公式计价：max(面积×单价/0.65, 面积×单价+1.5)，面积含 1.05 损耗系数。",
  },
  {
    key: "corrugated_box_price",
    label: "纸箱整箱单价覆盖",
    unit: "元/箱",
    default: "",
    grade: "C",
    help: "留空走按面积公式；填写后直接采用该整箱单价。",
  },
  { key: "pallet_purchase_price", label: "木托盘采购价", unit: "元", default: 110, low: 80, typical: 110, high: 180, grade: "B" },
  { key: "pallet_reuse_count", label: "托盘复用次数", unit: "次", default: 5, grade: "B" },
  { key: "stretch_film_unit_price_per_kg", label: "缠绕膜单价", unit: "元/kg", default: 11, low: 8.5, typical: 11, high: 14, grade: "B" },
  { key: "stretch_film_kg_per_pallet", label: "缠绕膜单托用量", unit: "kg/托", default: 0.8, grade: "B" },
  { key: "packing_band_price_per_pallet", label: "打包带单价", unit: "元/托", default: 3, low: 1.5, typical: 3, high: 8, grade: "B" },
  {
    key: "mold_tooling_cost",
    label: "EPS 模具总费用",
    unit: "元",
    default: "",
    grade: "C",
    help: "仅在实际采用 EPS 成型缓冲且允许开模时参与计算；填写后与摊销数量自动计算每台摊销。",
  },
  {
    key: "mold_amortize_qty",
    label: "EPS 模具摊销数量",
    unit: "台",
    default: "",
    grade: "C",
    help: "与模具总费用配套填写，公式：模具摊销/台 = 模具总费用 ÷ 摊销数量。",
  },
  {
    key: "mold_amortize_per_unit",
    label: "EPS 模具摊销/台覆盖",
    unit: "元/台",
    default: 3.33,
    grade: "C",
    help: "未填写模具总费用和摊销数量时，可直接输入每台摊销；都留空则使用系统默认 3.33 元/台。",
  },
  {
    key: "anti_static_bag_price_per_unit",
    label: "防静电袋单价",
    unit: "元/台",
    default: 1.2,
    low: 0.5,
    typical: 1.2,
    high: 3.5,
    grade: "D",
    help: "按近年防静电包装采购价范围预置；如产品不需要或供应商另报，可手动覆盖为 0 或实际单价。",
  },
  {
    key: "corner_protector_price_per_pallet",
    label: "护角单价",
    unit: "元/托",
    default: 8,
    low: 3,
    typical: 8,
    high: 18,
    grade: "D",
    help: "填写且勾选护角后按每托摊销。",
  },
  {
    key: "edge_protector_price_per_pallet",
    label: "护边单价",
    unit: "元/托",
    default: 8,
    low: 3,
    typical: 8,
    high: 20,
    grade: "D",
    help: "填写且勾选护边后按每托摊销。",
  },
];
