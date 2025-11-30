# دليل الترجمة العربية للمبالغ
# Arabic Translation Guide for Amount to Text

## 📋 المتطلبات (Requirements)

### 1. تثبيت مكتبة num2words

```bash
pip3 install num2words
```

أو إذا كنت تستخدم Odoo في بيئة افتراضية:

```bash
source /path/to/odoo-venv/bin/activate
pip install num2words
```

---

## ⚙️ الإعداد (Setup)

### 1. تفعيل اللغة العربية

1. اذهب إلى: **Settings → Translations → Languages**
2. ابحث عن **Arabic / العربية**
3. اضغط **Activate**

### 2. تعيين اللغة للمستخدم

1. اذهب إلى: **Settings → Users & Companies → Users**
2. اختر المستخدم
3. في تبويب **Preferences**
4. اختر **Language: العربية / Arabic**

### 3. تحديث تسميات العملة (اختياري)

الموديول يحدث تلقائياً تسميات العملات التالية:
- **EGP**: جنيه / قرش
- **USD**: دولار / سنت
- **SAR**: ريال / هللة
- **AED**: درهم / فلس
- **KWD**: دينار / فلس

لتحديث عملة أخرى يدوياً:
1. اذهب إلى: **Settings → Accounting → Currencies**
2. اختر العملة
3. حدث:
   - **Currency Unit Label**: (مثل: جنيه، دولار، ريال)
   - **Currency Subunit Label**: (مثل: قرش، سنت، هللة)

---

## 🎯 كيفية الاستخدام (Usage)

### في التقارير (In Reports)

الموديول يوفر دالة `amount_to_text_with_lang()` التي تحول المبلغ تلقائياً حسب لغة المستخدم:

```xml
<!-- سيظهر بالعربية إذا كانت لغة المستخدم عربية -->
<span t-esc="o.amount_to_text_with_lang()"/>
```

### في Python Code

```python
# للحصول على المبلغ بالعربية
payment = self.env['account.payment'].browse(payment_id)
amount_in_arabic = payment.amount_to_text_arabic()

# للحصول على المبلغ حسب لغة المستخدم
amount_in_words = payment.amount_to_text_with_lang()
```

---

## 📝 أمثلة (Examples)

### مثال 1: مبلغ بالجنيه المصري

**المبلغ:** 1250.75 EGP

**بالإنجليزية:**
```
One Thousand Two Hundred Fifty Dollars and Seventy-Five Cents
```

**بالعربية:**
```
ألف و مائتان و خمسون جنيه و خمسة و سبعون قرش
```

### مثال 2: مبلغ بالريال السعودي

**المبلغ:** 500.00 SAR

**بالعربية:**
```
خمسمائة ريال
```

---

## 🔧 استكشاف الأخطاء (Troubleshooting)

### المشكلة: المبلغ لا يظهر بالعربية

**الحل:**
1. تأكد من تثبيت `num2words`:
   ```bash
   pip3 show num2words
   ```

2. تأكد من تفعيل اللغة العربية في Odoo

3. تأكد من تعيين لغة المستخدم إلى العربية

4. أعد تشغيل Odoo:
   ```bash
   sudo systemctl restart odoo
   ```

### المشكلة: ظهور خطأ "num2words not found"

**الحل:**
```bash
# تثبيت المكتبة
pip3 install num2words

# إعادة تشغيل Odoo
sudo systemctl restart odoo
```

### المشكلة: تسميات العملة لا تظهر بالعربية

**الحل:**
1. اذهب إلى: **Settings → Accounting → Currencies**
2. اختر العملة (مثل EGP)
3. حدث الحقول:
   - **Currency Unit Label**: جنيه
   - **Currency Subunit Label**: قرش
4. احفظ التغييرات

---

## 📚 ملاحظات إضافية (Additional Notes)

- الدالة `amount_to_text_with_lang()` تكتشف تلقائياً لغة المستخدم
- إذا فشلت الترجمة العربية، ستعود تلقائياً للإنجليزية
- يمكنك تخصيص تسميات العملة لأي عملة أخرى
- المكتبة `num2words` تدعم أكثر من 30 لغة

---

## 🌐 اللغات المدعومة (Supported Languages)

المكتبة `num2words` تدعم:
- العربية (ar)
- الإنجليزية (en)
- الفرنسية (fr)
- الإسبانية (es)
- الألمانية (de)
- وغيرها...

---

## 📞 الدعم (Support)

للمزيد من المساعدة، راجع:
- [Odoo Documentation](https://www.odoo.com/documentation)
- [num2words GitHub](https://github.com/savoirfairelinux/num2words)

