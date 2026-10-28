# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError


class TestWeaving(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "عميل أقمشة تجريبي"})
        cls.fabric_product = cls.env["product.product"].create({
            "name": "قماش خام سنجل جيرسي قطن",
            "is_storable": True,
        })
        cls.yarn_cotton = cls.env["product.product"].create({
            "name": "غزل قطن 30/1 مشط",
            "is_storable": True,
            "standard_price": 120.0,
        })
        cls.yarn_lycra = cls.env["product.product"].create({
            "name": "غزل ليكرا 40D",
            "is_storable": True,
            "standard_price": 250.0,
        })
        # ماكينة نسيج دائري
        cls.circular_machine = cls.env["thamar.weaving.machine"].create({
            "name": "ماكينة دائري سنبل 1",
            "code": "CIRC-01",
            "weaving_type": "circular",
            "diameter_inch": 30.0,
            "gauge": "28GG",
            "feeders_count": 96,
            "rpm": 25.0,
            "electricity_cost_hour": 30.0,
            "labor_cost_hour": 40.0,
            "spare_parts_cost_hour": 15.0,
            "other_cost_hour": 15.0,
        })
        # ماكينة نسيج مستطيل (نول)
        cls.rectangular_machine = cls.env["thamar.weaving.machine"].create({
            "name": "نول رابير 10",
            "code": "LOOM-10",
            "weaving_type": "rectangular",
            "reed_width_cm": 220.0,
            "loom_type": "rapier",
            "speed_ppm": 550.0,
            "shafts_count": 16,
            "electricity_cost_hour": 35.0,
            "labor_cost_hour": 45.0,
            "spare_parts_cost_hour": 20.0,
            "other_cost_hour": 10.0,
        })

    def test_01_machine_cost_calculation(self):
        """التحقق من حساب إجمالي تكلفة الساعة للماكينات"""
        self.assertEqual(self.circular_machine.hourly_cost, 100.0)
        self.assertEqual(self.rectangular_machine.hourly_cost, 110.0)

    def test_02_weaving_order_and_yarn(self):
        """التحقق من إنشاء أمر تشغيل وإضافة خيوط الغزل والتكاليف"""
        order = self.env["thamar.weaving.order"].create({
            "weaving_type": "circular",
            "machine_id": self.circular_machine.id,
            "product_id": self.fabric_product.id,
            "partner_id": self.partner.id,
            "is_internal": False,
            "planned_weight_kg": 500.0,
            "target_gsm": 180.0,
            "target_width_cm": 180.0,
            "stitch_length_mm": 2.8,
            "yarn_line_ids": [
                (0, 0, {
                    "product_id": self.yarn_cotton.id,
                    "yarn_role": "ground",
                    "yarn_count": "30/1",
                    "blend_percentage": 95.0,
                    "planned_qty_kg": 475.0,
                    "consumed_qty_kg": 480.0,
                    "unit_cost": 120.0,
                }),
                (0, 0, {
                    "product_id": self.yarn_lycra.id,
                    "yarn_role": "lycra",
                    "yarn_count": "40D",
                    "blend_percentage": 5.0,
                    "planned_qty_kg": 25.0,
                    "consumed_qty_kg": 25.0,
                    "unit_cost": 250.0,
                }),
            ],
        })

        self.assertEqual(order.total_yarn_planned_kg, 500.0)
        self.assertEqual(order.total_yarn_consumed_kg, 505.0)
        expected_cost = (480.0 * 120.0) + (25.0 * 250.0)
        self.assertEqual(order.total_yarn_cost, expected_cost)

        # تأكيد وبدء الأمر
        order.action_confirm()
        self.assertEqual(order.state, "confirmed")
        order.action_start()
        self.assertEqual(order.state, "in_progress")
        self.assertEqual(self.circular_machine.state, "running")

    def test_03_roll_production_and_lot_sync(self):
        """التحقق من نزول ثوب وإنشاء لوط المخزون stock.lot ومزامنته بالخصائص"""
        order = self.env["thamar.weaving.order"].create({
            "weaving_type": "circular",
            "machine_id": self.circular_machine.id,
            "product_id": self.fabric_product.id,
            "planned_weight_kg": 100.0,
            "yarn_line_ids": [
                (0, 0, {
                    "product_id": self.yarn_cotton.id,
                    "yarn_role": "ground",
                    "planned_qty_kg": 100.0,
                    "consumed_qty_kg": 105.0,
                    "unit_cost": 100.0,
                }),
            ],
        })
        order.action_confirm()
        order.action_start()

        # إنشاء ثوب
        roll = self.env["thamar.weaving.roll"].create({
            "order_id": order.id,
            "lot_name": "LOT-TEST-CIRC-01",
            "gross_weight_kg": 25.5,
            "tare_weight_kg": 0.5,
            "length_meter": 80.0,
            "measured_gsm": 180.0,
            "measured_width_cm": 185.0,
            "grade": "grade_a",
        })

        # التحقق من الوزن الصافي
        self.assertEqual(roll.net_weight_kg, 25.0)

        # التحقق من إنشاء لوط المخزون ومطابقة الخصائص الفنية
        self.assertTrue(roll.lot_id)
        self.assertEqual(roll.lot_id.name, "LOT-TEST-CIRC-01")
        self.assertEqual(roll.lot_id.net_weight_kg, 25.0)
        self.assertEqual(roll.lot_id.fabric_grade, "grade_a")
        self.assertEqual(roll.lot_id.fabric_gsm, 180.0)
        self.assertEqual(roll.lot_id.weaving_type, "circular")

        # التحقق من إحصائيات أمر التشغيل
        self.assertEqual(order.roll_count, 1)
        self.assertEqual(order.total_net_weight_kg, 25.0)
        self.assertEqual(order.grade_a_weight_kg, 25.0)

        # فحص الهالك
        # غزل مستهلك = 105، صافي منتج = 25 -> هالك 80
        self.assertEqual(order.waste_weight_kg, 80.0)

    def test_04_transfer_roll_to_dyeing(self):
        """التحقق من زر تحويل اللوط مباشرة إلى موديول الطباعة والصباغة"""
        order = self.env["thamar.weaving.order"].create({
            "weaving_type": "rectangular",
            "machine_id": self.rectangular_machine.id,
            "product_id": self.fabric_product.id,
            "partner_id": self.partner.id,
            "planned_weight_kg": 200.0,
            "yarn_line_ids": [
                (0, 0, {
                    "product_id": self.yarn_cotton.id,
                    "yarn_role": "warp",
                    "planned_qty_kg": 200.0,
                    "consumed_qty_kg": 200.0,
                    "unit_cost": 100.0,
                }),
            ],
        })
        order.action_confirm()
        order.action_start()

        roll = self.env["thamar.weaving.roll"].create({
            "order_id": order.id,
            "lot_name": "LOT-RECT-LOOM-01",
            "gross_weight_kg": 50.8,
            "tare_weight_kg": 0.8,
            "length_meter": 150.0,
            "measured_gsm": 220.0,
            "measured_width_cm": 210.0,
            "grade": "grade_a",
        })

        action = roll.action_create_dyeing_work_order()
        self.assertTrue(action)
        self.assertEqual(roll.state, "delivered_dyeing")
        self.assertTrue(roll.dyeing_work_order_id)
        # التحقق من أن أمر الصباغة استلم نفس رقم اللوط والوزن والأمتار
        dyeing_order = roll.dyeing_work_order_id
        self.assertEqual(dyeing_order.message_number, "LOT-RECT-LOOM-01")
        self.assertEqual(dyeing_order.planned_weight_kg, 50.0)
        self.assertEqual(dyeing_order.planned_meter, 150.0)
