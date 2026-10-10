# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, new_test_user


class TestPrintingDyeing(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Test Fabric Customer"})
        cls.product = cls.env["product.product"].create({"name": "Cotton"})
        cls.chemical_product = cls.env["product.product"].create(
            {"name": "Test Dye Chemical", "is_storable": True}
        )
        cls.stage_dye = cls.env.ref("thamar_printing_dyeing.stage_type_dyehouse")
        cls.stage_finish = cls.env.ref("thamar_printing_dyeing.stage_type_finishing")
        cls.stage_preparation = cls.env.ref(
            "thamar_printing_dyeing.stage_type_preparation"
        )
        cls.machine = cls.env["thamar.dyeing.machine"].create(
            {
                "name": "Test Jet",
                "stage_type_ids": [(6, 0, [cls.stage_dye.id])],
                "capacity_kg": 500,
                "water_cost_hour": 10,
                "electricity_cost_hour": 20,
                "gas_cost_hour": 30,
                "other_cost_hour": 5,
            }
        )

    def _create_order(self, planned_weight=300, message_number="LOT-100"):
        return self.env["thamar.dyeing.work.order"].create(
            {
                "partner_id": self.partner.id,
                "message_number": message_number,
                "product_id": self.product.id,
                "planned_weight_kg": planned_weight,
                "operation_ids": [
                    (0, 0, {"sequence": 10, "stage_type_id": self.stage_dye.id}),
                    (0, 0, {"sequence": 20, "stage_type_id": self.stage_finish.id}),
                ],
            }
        )

    def test_plan_and_operations_are_data_entry_without_state_transitions(self):
        order = self._create_order()
        operations = order.operation_ids.sorted("sequence")
        self.assertEqual(order.state, "draft")
        self.assertEqual(operations[0].state, "waiting")
        self.assertEqual(operations[0].weight_kg, 300)
        operations[0].write({"exit_time": datetime(2026, 1, 1, 10, 0, 0)})
        self.assertEqual(operations[0].exit_time, datetime(2026, 1, 1, 10, 0, 0))
        self.assertEqual(operations[0].state, "waiting")

    def test_duration_and_machine_cost(self):
        order = self._create_order()
        operation = order.operation_ids.sorted("sequence")[0]
        operation.write(
            {
                "machine_id": self.machine.id,
                "entry_time": datetime(2026, 1, 1, 8, 0, 0),
                "exit_time": datetime(2026, 1, 1, 10, 30, 0),
            }
        )
        self.assertEqual(self.machine.hourly_cost, 65)
        self.assertEqual(operation.duration_hours, 2.5)
        self.assertEqual(operation.total_cost, 162.5)
        self.assertEqual(order.actual_start_time, operation.entry_time)
        self.assertEqual(order.actual_end_time, operation.exit_time)

    def test_preparation_propagates_actual_quantities(self):
        order = self.env["thamar.dyeing.work.order"].create(
            {
                "partner_id": self.partner.id,
                "message_number": "LOT-ACTUAL",
                "product_id": self.product.id,
                "planned_weight_kg": 300,
                "planned_meter": 1200,
                "operation_ids": [
                    (
                        0,
                        0,
                        {
                            "sequence": 10,
                            "stage_type_id": self.stage_preparation.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {"sequence": 20, "stage_type_id": self.stage_finish.id},
                    ),
                ],
            }
        )
        self.assertFalse(order.actual_quantities_set)
        preparation, finishing = order.operation_ids.sorted("sequence")
        preparation.write({"weight_kg": 285, "meter": 1160})
        self.assertTrue(order.actual_quantities_set)
        self.assertEqual(order.actual_weight_kg, 285)
        self.assertEqual(order.actual_meter, 1160)
        self.assertEqual(finishing.weight_kg, 285)
        self.assertEqual(finishing.meter, 1160)

    def test_wrong_machine_stage_is_rejected(self):
        order = self._create_order()
        finishing_operation = order.operation_ids.sorted("sequence")[1]
        with self.assertRaises(ValidationError):
            finishing_operation.machine_id = self.machine

    def test_machine_can_support_multiple_stages(self):
        shared_machine = self.env["thamar.dyeing.machine"].create(
            {
                "name": "Shared Test Machine",
                "stage_type_ids": [
                    (6, 0, [self.stage_dye.id, self.stage_finish.id])
                ],
            }
        )
        order = self._create_order()
        for operation in order.operation_ids:
            operation.machine_id = shared_machine
        self.assertEqual(order.operation_ids.mapped("machine_id"), shared_machine)

    def test_default_ram_supports_all_configured_operations(self):
        ram = self.env.ref("thamar_printing_dyeing.machine_ram_01")
        expected_stages = self.env["thamar.dyeing.stage.type"].browse(
            [
                self.env.ref("thamar_printing_dyeing.stage_type_heat_setting").id,
                self.env.ref("thamar_printing_dyeing.stage_type_final_finishing").id,
                self.env.ref(
                    "thamar_printing_dyeing.stage_type_carbon_preparation"
                ).id,
                self.env.ref(
                    "thamar_printing_dyeing.stage_type_casting_preparation"
                ).id,
                self.env.ref(
                    "thamar_printing_dyeing.stage_type_compactor_preparation"
                ).id,
                self.env.ref(
                    "thamar_printing_dyeing.stage_type_calender_preparation"
                ).id,
                self.env.ref(
                    "thamar_printing_dyeing.stage_type_printing_preparation"
                ).id,
            ]
        )
        self.assertTrue(expected_stages <= ram.stage_type_ids)

    def test_jet_batch_runs_multiple_plans_and_allocates_cost(self):
        first_order = self._create_order(
            planned_weight=300, message_number="LOT-BATCH-1"
        )
        second_order = self._create_order(
            planned_weight=200, message_number="LOT-BATCH-2"
        )
        first_dye = first_order.operation_ids.sorted("sequence")[0]
        second_dye = second_order.operation_ids.sorted("sequence")[0]

        batch = self.env["thamar.dyeing.batch"].create(
            {
                "stage_type_id": self.stage_dye.id,
                "machine_id": self.machine.id,
                "worker_name": "Jet Operator",
                "entry_time": datetime(2026, 1, 1, 8, 0, 0),
                "operation_ids": [(6, 0, [first_dye.id, second_dye.id])],
            }
        )
        self.assertEqual(batch.work_order_count, 2)
        self.assertEqual(batch.total_weight_kg, 500)

        self.assertEqual(first_dye.machine_id, self.machine)
        self.assertEqual(second_dye.worker_name, "Jet Operator")
        self.assertEqual(first_dye.entry_time, batch.entry_time)
        self.assertEqual(second_dye.entry_time, batch.entry_time)

        batch.exit_time = batch.entry_time + timedelta(hours=2)
        self.assertEqual(first_dye.exit_time, batch.exit_time)
        self.assertEqual(second_dye.exit_time, batch.exit_time)
        self.assertEqual(batch.total_cost, 130)
        self.assertAlmostEqual(first_dye.total_cost, 78)
        self.assertAlmostEqual(second_dye.total_cost, 52)
        self.assertAlmostEqual(first_dye.total_cost + second_dye.total_cost, 130)
        self.assertEqual(first_order.actual_end_time, batch.exit_time)
        self.assertEqual(second_order.actual_end_time, batch.exit_time)

    def test_operation_cannot_join_two_batches(self):
        order = self._create_order(planned_weight=200, message_number="LOT-ONLY-ONE")
        operation = order.operation_ids.sorted("sequence")[0]
        self.env["thamar.dyeing.batch"].create(
            {
                "stage_type_id": self.stage_dye.id,
                "machine_id": self.machine.id,
                "operation_ids": [(6, 0, operation.ids)],
            }
        )
        with self.assertRaises(ValidationError):
            self.env["thamar.dyeing.batch"].create(
                {
                    "stage_type_id": self.stage_dye.id,
                    "machine_id": self.machine.id,
                    "operation_ids": [(6, 0, operation.ids)],
                }
            )

    def test_material_issue_is_linked_to_plan_and_operation(self):
        order = self._create_order(message_number="LOT-MATERIALS")
        operation = order.operation_ids.sorted("sequence")[0]
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        picking_type = warehouse.int_type_id
        source_location = warehouse.lot_stock_id
        destination_location = self.env["stock.location"].search(
            [
                ("usage", "=", "production"),
                "|",
                ("company_id", "=", self.env.company.id),
                ("company_id", "=", False),
            ],
            order="company_id desc, id",
            limit=1,
        )
        self.env["stock.quant"]._update_available_quantity(
            self.chemical_product, source_location, 10
        )
        picking = self.env["stock.picking"].create(
            {
                "is_dyeing_material_issue": True,
                "dyeing_work_order_id": order.id,
                "dyeing_operation_id": operation.id,
                "picking_type_id": picking_type.id,
                "location_id": source_location.id,
                "location_dest_id": destination_location.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.chemical_product.id,
                            "product_uom_qty": 4,
                            "product_uom": self.chemical_product.uom_id.id,
                            "location_id": source_location.id,
                            "location_dest_id": destination_location.id,
                        },
                    )
                ],
            }
        )
        self.assertEqual(picking.dyeing_work_order_id, order)
        self.assertEqual(picking.dyeing_operation_id, operation)
        self.assertEqual(operation.material_issue_ids, picking)
        self.assertEqual(operation.material_move_ids, picking.move_ids)

        picking.action_confirm()
        picking.action_assign()
        picking.move_ids.quantity = 4
        picking.move_ids.picked = True
        picking.button_validate()

        self.assertEqual(picking.state, "done")
        self.assertEqual(operation.material_move_ids.quantity, 4)
        remaining_quantity = self.env["stock.quant"]._get_available_quantity(
            self.chemical_product, source_location
        )
        self.assertEqual(remaining_quantity, 6)

    def test_only_manager_can_change_customer_from_operation(self):
        regular_user = new_test_user(
            self.env,
            login="dyeing_regular_user",
            groups="thamar_printing_dyeing.group_printing_dyeing_user",
        )
        manager = new_test_user(
            self.env,
            login="dyeing_manager_user",
            groups="thamar_printing_dyeing.group_printing_dyeing_manager",
        )
        new_partner = self.env["res.partner"].create({"name": "Changed Customer"})
        order = self._create_order()
        operation = order.operation_ids[0]
        messages_before = operation.message_ids
        with self.assertRaises(AccessError):
            operation.with_user(regular_user).write({"partner_id": new_partner.id})
        operation.with_user(manager).write({"partner_id": new_partner.id})
        self.assertEqual(order.partner_id, new_partner)
        self.assertEqual(operation.partner_id, new_partner)
        customer_tracking = operation.message_ids - messages_before
        self.assertTrue(
            any(
                "تم تغيير العميل" in (message.body or "")
                for message in customer_tracking
            )
        )

    def test_empty_plan_is_allowed_for_data_entry(self):
        order = self.env["thamar.dyeing.work.order"].create(
            {
                "partner_id": self.partner.id,
                "message_number": "LOT-EMPTY",
                "product_id": self.product.id,
            }
        )
        self.assertFalse(order.operation_ids)
