# اختبار الترجمة العربية للمبالغ
# Test Arabic Amount Translation

## 🧪 كيفية الاختبار (How to Test)

### الطريقة 1: من واجهة Odoo

1. **قم بترقية الموديول:**
   - اذهب إلى: **Apps**
   - ابحث عن: **Thamar Invoice Customization**
   - اضغط: **Upgrade**

2. **تفعيل اللغة العربية:**
   - اذهب إلى: **Settings → Translations → Languages**
   - فعّل: **Arabic / العربية**

3. **تغيير لغة المستخدم:**
   - اذهب إلى: **Settings → Users**
   - اختر المستخدم الحالي
   - في **Preferences → Language**: اختر **العربية / Arabic**
   - احفظ

4. **إنشاء دفعة تجريبية:**
   - اذهب إلى: **Accounting → Customers → Payments**
   - اضغط: **Create**
   - املأ البيانات:
     - **Customer**: اختر عميل
     - **Amount**: 1250.75
     - **Currency**: EGP (أو أي عملة)
   - احفظ

5. **طباعة الإيصال:**
   - اضغط: **Print → Custom Payment Receipt**
   - يجب أن ترى المبلغ بالعربية:
     ```
     ألف و مائتان و خمسون جنيه و خمسة و سبعون قرش
     ```

---

### الطريقة 2: من Python Shell

```bash
# افتح Odoo shell
./odoo-bin shell -d your_database_name
```

```python
# اختبار الترجمة العربية
payment = env['account.payment'].search([], limit=1)

# اختبار بالعربية
print("Arabic:", payment.amount_to_text_arabic())

# اختبار حسب اللغة
print("Auto:", payment.amount_to_text_with_lang())

# اختبار مع سياق عربي
payment_ar = payment.with_context(lang='ar_001')
print("Context AR:", payment_ar.amount_to_text_with_lang())

# اختبار مع سياق إنجليزي
payment_en = payment.with_context(lang='en_US')
print("Context EN:", payment_en.amount_to_text_with_lang())
```

---

## ✅ النتائج المتوقعة (Expected Results)

### مثال 1: 1250.75 EGP

**بالإنجليزية:**
```
One Thousand Two Hundred Fifty Dollars and Seventy-Five Cents
```

**بالعربية:**
```
ألف و مائتان و خمسون جنيه و خمسة و سبعون قرش
```

---

### مثال 2: 500.00 SAR

**بالإنجليزية:**
```
Five Hundred Dollars
```

**بالعربية:**
```
خمسمائة ريال
```

---

### مثال 3: 99.99 USD

**بالإنجليزية:**
```
Ninety-Nine Dollars and Ninety-Nine Cents
```

**بالعربية:**
```
تسعة و تسعون دولار و تسعة و تسعون سنت
```

---

## 🔍 التحقق من التثبيت (Verify Installation)

### 1. التحقق من num2words

```bash
python3 -c "import num2words; print(num2words.num2words(123, lang='ar'))"
```

**النتيجة المتوقعة:**
```
مائة و ثلاثة و عشرون
```

---

### 2. التحقق من الموديول

```bash
# من Odoo shell
./odoo-bin shell -d your_database_name
```

```python
# التحقق من وجود الدالة
payment = env['account.payment'].search([], limit=1)
print(hasattr(payment, 'amount_to_text_arabic'))  # يجب أن يكون True
print(hasattr(payment, 'amount_to_text_with_lang'))  # يجب أن يكون True
```

---

## 🐛 استكشاف الأخطاء (Debugging)

### إذا لم تظهر الترجمة العربية:

1. **تحقق من السجلات (Logs):**
   ```bash
   tail -f /var/log/odoo/odoo-server.log
   ```

2. **تحقق من تثبيت num2words:**
   ```bash
   pip3 list | grep num2words
   ```

3. **تحقق من لغة المستخدم:**
   ```python
   # من Odoo shell
   user = env.user
   print("User Language:", user.lang)
   ```

4. **اختبار مباشر:**
   ```python
   from num2words import num2words
   print(num2words(1250, lang='ar'))
   ```

---

## 📊 حالات اختبار إضافية (Additional Test Cases)

| المبلغ | العملة | النتيجة المتوقعة بالعربية |
|--------|--------|---------------------------|
| 0.00 | EGP | صفر جنيه |
| 1.00 | EGP | واحد جنيه |
| 10.50 | EGP | عشرة جنيه و خمسون قرش |
| 100.00 | SAR | مائة ريال |
| 1000.25 | USD | ألف دولار و خمسة و عشرون سنت |
| 999999.99 | AED | تسعمائة و تسعة و تسعون ألف و تسعمائة و تسعة و تسعون درهم و تسعة و تسعون فلس |

---

## ✨ ملاحظات (Notes)

- الترجمة تعتمد على لغة المستخدم الحالي
- إذا فشلت الترجمة العربية، سيتم استخدام الإنجليزية تلقائياً
- يمكنك تخصيص تسميات العملة من إعدادات Odoo
- الدالة تدعم جميع العملات المعرفة في النظام

