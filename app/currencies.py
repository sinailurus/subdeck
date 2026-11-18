# -*- coding: utf-8 -*-
"""SubDeck 支持的币种与周期定义。

币种列表取自欧洲央行（ECB）参考汇率所覆盖的币种，
汇率数据通过 frankfurter.dev 开放接口获取（免费、无需密钥）。
"""

# 所有内置币种（ECB 参考汇率覆盖范围）
CURRENCIES = [
    "CNY", "USD", "EUR", "JPY", "GBP", "HKD", "TWD", "KRW", "SGD",
    "AUD", "CAD", "CHF", "SEK", "NOK", "DKK", "PLN", "CZK", "HUF",
    "BRL", "MXN", "IDR", "INR", "ILS", "PHP", "THB", "MYR", "NZD",
    "TRY", "ZAR", "ISK",
]

# 周期定义：key -> (英文名, 中文名, 月度折算系数)
# monthly_normalized = 金额 × 月度系数
CYCLES = {
    "weekly":     ("Weekly",     "每周",   52.0 / 12.0),
    "monthly":    ("Monthly",    "每月",   1.0),
    "quarterly":  ("Quarterly",  "每季度", 1.0 / 3.0),
    "semiannual": ("Semiannual", "每半年", 1.0 / 6.0),
    "yearly":     ("Yearly",     "每年",   1.0 / 12.0),
}

# 付款方式
PAYMENT_METHODS = {
    "auto":   ("Auto",   "自动扣费"),
    "manual": ("Manual", "手动付款"),
}

# 常用分类（用户也可自行输入）
CATEGORIES = [
    "video", "music", "cloud", "software", "network",
    "game", "news", "shopping", "other",
]
