# -*- coding: utf-8 -*-
"""Move existing single-stage machine links to the new multi-stage relation."""


def migrate(cr, version):
    cr.execute(
        """
        SELECT EXISTS (
            SELECT 1
              FROM information_schema.columns
             WHERE table_name = 'thamar_dyeing_machine'
               AND column_name = 'stage_type_id'
        )
        """
    )
    if cr.fetchone()[0]:
        cr.execute(
            """
            INSERT INTO thamar_dyeing_machine_stage_rel (machine_id, stage_type_id)
                 SELECT id, stage_type_id
                   FROM thamar_dyeing_machine
                  WHERE stage_type_id IS NOT NULL
            ON CONFLICT DO NOTHING
            """
        )

    ram_xmlids = tuple(f"machine_ram_0{number}" for number in range(1, 7))
    ram_stage_xmlids = (
        "stage_type_finishing",
        "stage_type_heat_setting",
        "stage_type_final_finishing",
        "stage_type_carbon_preparation",
        "stage_type_casting_preparation",
        "stage_type_compactor_preparation",
        "stage_type_calender_preparation",
        "stage_type_printing_preparation",
    )
    cr.execute(
        """
        INSERT INTO thamar_dyeing_machine_stage_rel (machine_id, stage_type_id)
             SELECT machine_data.res_id, stage_data.res_id
               FROM ir_model_data AS machine_data
         CROSS JOIN ir_model_data AS stage_data
              WHERE machine_data.module = 'thamar_printing_dyeing'
                AND machine_data.name IN %s
                AND machine_data.model = 'thamar.dyeing.machine'
                AND stage_data.module = 'thamar_printing_dyeing'
                AND stage_data.name IN %s
                AND stage_data.model = 'thamar.dyeing.stage.type'
        ON CONFLICT DO NOTHING
        """,
        (ram_xmlids, ram_stage_xmlids),
    )

