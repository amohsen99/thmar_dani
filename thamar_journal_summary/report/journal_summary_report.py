# -*- coding: utf-8 -*-

from datetime import timedelta

from odoo import api, models, fields

# Account types where debit = increase (asset & expense families)
DEBIT_NATURE_PREFIXES = ('asset', 'expense')


class ReportJournalSummary(models.AbstractModel):
    _name = 'report.thamar_journal_summary.report_journal_summary'
    _description = 'Account Analysis Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Route to the correct computation based on report_type."""
        report_type = data.get('report_type', 'compound_entry')
        account_ids = data.get('account_ids', [])
        date_from = fields.Date.from_string(data.get('date_from'))
        date_to = fields.Date.from_string(data.get('date_to'))

        # Column visibility flags (default to legacy behaviour)
        show_ending_balance = data.get('show_ending_balance', True)
        show_cheque_number = data.get('show_cheque_number', False)
        show_bank_name = data.get('show_bank_name', False)
        show_cheque_due_date = data.get('show_cheque_due_date', False)
        show_analytic = data.get('show_analytic', False)
        show_analytic_distribution = data.get('show_analytic_distribution', False)

        accounts = self.env['account.account'].browse(account_ids)

        if report_type == 'compound_entry':
            accounts_data = self._compute_compound_entry(accounts, date_from, date_to)
        else:
            accounts_data = self._compute_running_ledger(accounts, date_from, date_to)

        return {
            'doc_ids': docids,
            'doc_model': 'journal.summary.wizard',
            'data': data,
            'report_type': report_type,
            'accounts_data': accounts_data,
            'company': self.env.company,
            # visibility flags for QWeb
            'show_ending_balance': show_ending_balance,
            'show_cheque_number': show_cheque_number,
            'show_bank_name': show_bank_name,
            'show_cheque_due_date': show_cheque_due_date,
            'show_analytic': show_analytic,
            'show_analytic_distribution': show_analytic_distribution,
        }

    # ==================================================================
    # REPORT TYPE 1: Compound Entry Analysis (Journal Entry Format)
    # ==================================================================

    def _compute_compound_entry(self, accounts, date_from, date_to):
        """Compute journal-entry-format lines for each account.

        For each account, produces two balanced sections (inflow/outflow)
        presented as compound journal entries with debit/credit columns,
        Arabic accounting prefixes (من حـ/ / إلى حـ/), and balanced totals.
        """
        results = []
        lang = self.env.context.get('lang', 'en_US')
        company_id = str(self.env.company.id)

        for account in accounts:
            is_debit_nature = account.account_type.startswith(DEBIT_NATURE_PREFIXES)
            acct_code = account.code or ''
            acct_name = account.name or ''

            # --- Inflows (increase) ---
            inflow_cps, total_inflow = self._query_counterparts(
                account.id,
                increase_side='debit' if is_debit_nature else 'credit',
                date_from=date_from, date_to=date_to,
                lang=lang, company_id=company_id,
            )

            # --- Outflows (decrease) ---
            outflow_cps, total_outflow = self._query_counterparts(
                account.id,
                increase_side='credit' if is_debit_nature else 'debit',
                date_from=date_from, date_to=date_to,
                lang=lang, company_id=company_id,
            )

            # Build journal entry lines for INFLOW section
            inflow_lines = self._build_je_lines(
                acct_code, acct_name, total_inflow, inflow_cps,
                target_on_debit=is_debit_nature,
                section_label='',
            )

            # Build journal entry lines for OUTFLOW section
            outflow_lines = self._build_je_lines(
                acct_code, acct_name, total_outflow, outflow_cps,
                target_on_debit=not is_debit_nature,
                section_label='',
            )

            # Grand totals (guaranteed balanced from balanced journal entries)
            all_lines = inflow_lines + outflow_lines
            grand_debit = sum(l['debit'] for l in all_lines)
            grand_credit = sum(l['credit'] for l in all_lines)

            results.append({
                'account_code': acct_code,
                'account_name': acct_name,
                'date_from': date_from,
                'date_to': date_to,
                'inflow_lines': inflow_lines,
                'outflow_lines': outflow_lines,
                'total_inflow': total_inflow,
                'total_outflow': total_outflow,
                'grand_total_debit': grand_debit,
                'grand_total_credit': grand_credit,
            })

        return results

    def _build_je_lines(self, acct_code, acct_name, target_total,
                        counterparts, target_on_debit, section_label):
        """Build journal entry lines for one section (inflow or outflow).

        Returns a list of dicts ready for QWeb rendering:
        - Debit-side lines first (من حـ/)
        - Credit-side lines second (إلى حـ/), indented
        """
        if not target_total:
            return []

        debit_lines = []
        credit_lines = []

        # Target account line
        target_line = {
            'description': f'{acct_code} - {acct_name}',
            'debit': float(target_total) if target_on_debit else 0.0,
            'credit': float(target_total) if not target_on_debit else 0.0,
            'notes': section_label,
            'is_debit_side': target_on_debit,
        }
        if target_on_debit:
            debit_lines.append(target_line)
        else:
            credit_lines.append(target_line)

        # Counterpart lines — each has both debit and credit sums
        for cp in counterparts:
            cp_debit = float(cp['debit'])
            cp_credit = float(cp['credit'])
            if cp_debit > 0:
                debit_lines.append({
                    'description': f"{cp['code']} - {cp['name']}",
                    'debit': cp_debit,
                    'credit': 0.0,
                    'notes': '',
                    'is_debit_side': True,
                })
            if cp_credit > 0:
                credit_lines.append({
                    'description': f"{cp['code']} - {cp['name']}",
                    'debit': 0.0,
                    'credit': cp_credit,
                    'notes': '',
                    'is_debit_side': False,
                })

        return debit_lines + credit_lines

    def _query_counterparts(self, account_id, increase_side, date_from, date_to,
                            lang, company_id):
        """Query counterpart accounts grouped by account, returning both
        debit and credit sums for journal entry balancing.

        Returns:
            (counterpart_list, total_target_amount)
        """
        if increase_side == 'debit':
            side_filter = "target.debit > 0"
            amount_expr = "target.debit"
        else:
            side_filter = "target.credit > 0"
            amount_expr = "target.credit"

        # Total on the target account for this direction
        self.env.cr.execute(f"""
            SELECT COALESCE(SUM({amount_expr}), 0)
              FROM account_move_line target
              JOIN account_move am ON am.id = target.move_id
             WHERE target.account_id = %(account_id)s
               AND {side_filter}
               AND target.date >= %(date_from)s
               AND target.date <= %(date_to)s
               AND am.state = 'posted'
        """, {
            'account_id': account_id,
            'date_from': date_from,
            'date_to': date_to,
        })
        total_amount = self.env.cr.fetchone()[0]

        # Counterpart accounts grouped with both debit and credit
        self.env.cr.execute(f"""
            SELECT cpart.account_id,
                   COALESCE(acc.code_store ->> %(company_id)s, ''),
                   COALESCE(acc.name ->> %(lang)s, acc.name ->> 'en_US', ''),
                   COALESCE(SUM(cpart.debit), 0) AS total_debit,
                   COALESCE(SUM(cpart.credit), 0) AS total_credit
              FROM account_move_line target
              JOIN account_move_line cpart ON cpart.move_id = target.move_id
                                          AND cpart.id != target.id
              JOIN account_account acc ON acc.id = cpart.account_id
              JOIN account_move am ON am.id = target.move_id
             WHERE target.account_id = %(account_id)s
               AND {side_filter}
               AND target.date >= %(date_from)s
               AND target.date <= %(date_to)s
               AND am.state = 'posted'
          GROUP BY cpart.account_id,
                   acc.code_store ->> %(company_id)s,
                   acc.name ->> %(lang)s,
                   acc.name ->> 'en_US'
          ORDER BY acc.code_store ->> %(company_id)s
        """, {
            'account_id': account_id,
            'date_from': date_from,
            'date_to': date_to,
            'company_id': company_id,
            'lang': lang,
        })

        counterparts = []
        for row in self.env.cr.fetchall():
            counterparts.append({
                'account_id': row[0],
                'code': row[1],
                'name': row[2],
                'debit': row[3],
                'credit': row[4],
            })

        return counterparts, total_amount

    # ==================================================================
    # REPORT TYPE 2: Running Ledger Statement
    # ==================================================================

    def _compute_running_ledger(self, accounts, date_from, date_to):
        """Compute running ledger with row-by-row cumulative balance."""
        results = []

        for account in accounts:
            # --- Opening Balance ---
            opening_balance = self._compute_account_balance(
                account.id, date_from - timedelta(days=1),
            )

            # --- Period Detail Lines ---
            detail_lines = self._fetch_period_lines(
                account.id, date_from, date_to,
            )

            # --- Compute running balance row by row ---
            running = opening_balance
            total_debit = 0.0
            total_credit = 0.0
            for line in detail_lines:
                running += line['debit'] - line['credit']
                line['running_balance'] = running
                total_debit += line['debit']
                total_credit += line['credit']

            closing_balance = opening_balance + total_debit - total_credit

            results.append({
                'account_code': account.code or '',
                'account_name': account.name or '',
                'date_from': date_from,
                'date_to': date_to,
                'opening_balance': opening_balance,
                'closing_balance': closing_balance,
                'total_debit': total_debit,
                'total_credit': total_credit,
                'detail_lines': detail_lines,
            })

        return results

    # ------------------------------------------------------------------
    # Shared helper methods
    # ------------------------------------------------------------------

    def _compute_account_balance(self, account_id, up_to_date):
        """Return sum(debit - credit) for posted entries up to and including up_to_date."""
        self.env.cr.execute("""
            SELECT COALESCE(SUM(aml.debit - aml.credit), 0)
              FROM account_move_line aml
              JOIN account_move am ON am.id = aml.move_id
             WHERE aml.account_id = %s
               AND aml.date <= %s
               AND am.state = 'posted'
        """, (account_id, up_to_date))
        return self.env.cr.fetchone()[0]

    def _fetch_period_lines(self, account_id, date_from, date_to):
        """Fetch individual move lines for the running ledger table.

        Returns list of dicts sorted by date, move name.
        Includes payment-related fields (cheque, bank) and analytic info.
        """
        self.env.cr.execute("""
            SELECT aml.date,
                   am.name                          AS move_name,
                   COALESCE(aml.name, '')            AS label,
                   COALESCE(rp.name, '')             AS partner_name,
                   aml.debit,
                   aml.credit,
                   COALESCE(ap.cheque_number, '')    AS cheque_number,
                   COALESCE(rb.name, '')             AS bank_name,
                   ap.cheque_due_date                AS cheque_due_date,
                   aml.analytic_distribution
              FROM account_move_line aml
              JOIN account_move am ON am.id = aml.move_id
         LEFT JOIN res_partner rp ON rp.id = aml.partner_id
         LEFT JOIN account_payment ap ON ap.move_id = am.id
         LEFT JOIN res_bank rb ON rb.id = ap.bank_id
             WHERE aml.account_id = %s
               AND aml.date >= %s
               AND aml.date <= %s
               AND am.state = 'posted'
          ORDER BY aml.date, am.name, aml.id
        """, (account_id, date_from, date_to))

        # Pre-fetch analytic account names for distribution rendering
        analytic_cache = {}

        lines = []
        for row in self.env.cr.fetchall():
            # Parse analytic distribution JSON → readable string
            distribution_raw = row[9]  # jsonb / dict or None
            analytic_names = []
            analytic_dist_text = ''
            if distribution_raw and isinstance(distribution_raw, dict):
                for analytic_id_str, pct in distribution_raw.items():
                    aid = int(analytic_id_str)
                    if aid not in analytic_cache:
                        aa = self.env['account.analytic.account'].browse(aid)
                        analytic_cache[aid] = aa.name or ''
                    name = analytic_cache[aid]
                    analytic_names.append(name)
                    analytic_dist_text += f"{name} ({pct}%)  "

            lines.append({
                'date': row[0],
                'move_name': row[1] or '',
                'label': row[2],
                'partner_name': row[3],
                'debit': float(row[4]),
                'credit': float(row[5]),
                'running_balance': 0.0,  # computed later
                'cheque_number': row[6] or '',
                'bank_name': row[7] or '',
                'cheque_due_date': row[8],
                'analytic_name': ', '.join(analytic_names),
                'analytic_distribution_text': analytic_dist_text.strip(),
            })
        return lines
