from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestCategoryBarcode(TransactionCase):
    def test_hierarchical_sequence_codes(self):
        parent = self.env["product.category"].create(
            {"name": "Test parent", "thamar_barcode_code": "88"}
        )
        category = self.env["product.category"].create(
            {
                "name": "Test leaf",
                "parent_id": parent.id,
                "thamar_barcode_code": "07",
                "thamar_barcode_mode": "sequence",
                "thamar_barcode_serial_digits": 4,
            }
        )

        first = self.env["product.template"].create(
            {"name": "First coded product", "categ_id": category.id}
        ).product_variant_id
        second = self.env["product.template"].create(
            {"name": "Second coded product", "categ_id": category.id}
        ).product_variant_id

        self.assertEqual(category.thamar_full_category_code, "8807")
        self.assertEqual(first.barcode, "88070001")
        self.assertEqual(first.default_code, first.barcode)
        self.assertEqual(second.barcode, "88070002")
        self.assertEqual(first.thamar_barcode_category_id, category)
        self.assertEqual(first.thamar_barcode_serial, "0001")

    def test_seeded_category_examples(self):
        cases = [
            ("category_yarn_polyester", "01010001"),
            ("category_raw_rectangular_polyester", "211001"),
            ("category_raw_circular_polyester", "2210001"),
            ("category_chemicals", "40001"),
            ("category_spare_parts", "50001"),
            ("category_miscellaneous", "60001"),
        ]
        for xml_id, expected in cases:
            category = self.env.ref("thamar_product_barcode_custom.%s" % xml_id)
            product = self.env["product.template"].create(
                {"name": "Example %s" % xml_id, "categ_id": category.id}
            ).product_variant_id
            self.assertEqual(product.barcode, expected)

    def test_fixed_waste_code_allows_one_variant(self):
        category = self.env.ref(
            "thamar_product_barcode_custom.category_printing_waste"
        )
        product = self.env["product.template"].create(
            {"name": "Printing waste", "categ_id": category.id}
        ).product_variant_id
        self.assertEqual(product.barcode, "3555555")

        with self.assertRaises(ValidationError):
            self.env["product.template"].create(
                {"name": "Duplicate printing waste", "categ_id": category.id}
            )

    def test_each_variant_gets_its_own_serial(self):
        category = self.env["product.category"].create(
            {
                "name": "Variant coding category",
                "thamar_barcode_code": "89",
                "thamar_barcode_mode": "sequence",
                "thamar_barcode_serial_digits": 3,
            }
        )
        attribute = self.env["product.attribute"].create(
            {"name": "Test color", "create_variant": "always"}
        )
        values = self.env["product.attribute.value"].create(
            [
                {"name": "Red", "attribute_id": attribute.id},
                {"name": "Blue", "attribute_id": attribute.id},
            ]
        )
        template = self.env["product.template"].create(
            {
                "name": "Product with two colors",
                "categ_id": category.id,
                "attribute_line_ids": [
                    Command.create(
                        {
                            "attribute_id": attribute.id,
                            "value_ids": [Command.set(values.ids)],
                        }
                    )
                ],
            }
        )

        self.assertEqual(len(template.product_variant_ids), 2)
        self.assertEqual(
            sorted(template.product_variant_ids.mapped("barcode")),
            ["89001", "89002"],
        )

    def test_used_hierarchy_and_generated_code_are_protected(self):
        parent = self.env["product.category"].create(
            {"name": "Protected parent", "thamar_barcode_code": "77"}
        )
        category = self.env["product.category"].create(
            {
                "name": "Protected leaf",
                "parent_id": parent.id,
                "thamar_barcode_code": "01",
                "thamar_barcode_mode": "sequence",
                "thamar_barcode_serial_digits": 3,
            }
        )
        template = self.env["product.template"].create(
            {"name": "Protected product", "categ_id": category.id}
        )
        other_category = self.env["product.category"].create(
            {"name": "Other uncoded category"}
        )

        with self.assertRaises(ValidationError):
            parent.write({"thamar_barcode_code": "78"})
        with self.assertRaises(ValidationError):
            template.product_variant_id.write({"barcode": "999"})
        with self.assertRaises(ValidationError):
            template.write({"categ_id": other_category.id})

    def test_non_coding_category_does_not_generate_code(self):
        category = self.env["product.category"].create(
            {"name": "Organizational category", "thamar_barcode_code": "91"}
        )
        product = self.env["product.template"].create(
            {"name": "Uncoded product", "categ_id": category.id}
        ).product_variant_id
        self.assertFalse(product.thamar_barcode_category_id)
        self.assertFalse(product.barcode)
