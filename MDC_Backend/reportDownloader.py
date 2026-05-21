"""
reportDownloader.py
───────────────────────────────────────────────────────────────────────────────
Psychological Report PDF generation for Milestones Developmental Center.

Exports:
  build_report_html(record)   → full A4 HTML string ready for xhtml2pdf
  HistorySheetPDFView         → Django REST APIView: GET /history-sheet/pdf/
"""

import io
import json
import traceback
from datetime import datetime

from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

# MongoDB connection reused from views
from .views import db, client


# ─── Helpers ──────────────────────────────────────────────────────────────────

def clean_record(record: dict) -> dict:
    """Recursively parse JSON strings in record into Python dicts/lists."""
    if not record:
        return {}
    cleaned = {}
    for k, v in record.items():
        if isinstance(v, str):
            stripped = v.strip()
            if (stripped.startswith('{') and stripped.endswith('}')) or (stripped.startswith('[') and stripped.endswith(']')):
                try:
                    cleaned[k] = json.loads(stripped)
                    # Recursively clean the parsed object
                    if isinstance(cleaned[k], dict):
                        cleaned[k] = clean_record(cleaned[k])
                    elif isinstance(cleaned[k], list):
                        cleaned[k] = [clean_record(item) if isinstance(item, dict) else item for item in cleaned[k]]
                    continue
                except Exception:
                    pass
        elif isinstance(v, dict):
            cleaned[k] = clean_record(v)
            continue
        elif isinstance(v, list):
            cleaned[k] = [clean_record(item) if isinstance(item, dict) else item for item in v]
            continue
        cleaned[k] = v
    return cleaned


def _fmt_date(s: str) -> str:
    if not s:
        return '–'
    try:
        d = datetime.fromisoformat(s.replace('Z', ''))
        return d.strftime('%d.%m.%Y')
    except Exception:
        return s


def _fmt_key(k: str) -> str:
    if not k:
        return ""
    s = k.replace('_', ' ').replace('-', ' ').strip()
    return s.capitalize()


def _calc_age(dob_s: str, assess_s: str) -> str:
    if not dob_s or not assess_s:
        return '–'
    try:
        dob    = datetime.fromisoformat(dob_s.replace('Z', ''))
        assess = datetime.fromisoformat(assess_s.replace('Z', ''))
        yrs = assess.year  - dob.year
        mos = assess.month - dob.month
        if mos < 0:
            yrs -= 1
            mos += 12
        if yrs:
            return f"{yrs} yr{'s' if yrs != 1 else ''} {mos} mo"
        return f"{mos} month{'s' if mos != 1 else ''}"
    except Exception:
        return '–'


def _imp_color(imp: str) -> str:
    l = (imp or '').lower()
    if l == 'achieved':  return '#1b5e20'
    if l == 'delayed':   return '#e65100'
    if 'not' in l:       return '#b71c1c'
    return '#555'


def _get_creator_signature(created_by: str) -> str:
    if not created_by:
        return ""
    try:
        db_global = client['Global']
        col = db_global['backend_diagnostics_profile']
        doc = col.find_one({'employeeId': str(created_by)})
        if doc:
            name = doc.get('employeeName', '').strip()
            # Prefix with Ms. / Mr. / Dr. if not present
            if not any(name.startswith(p) for p in ['Dr.', 'Mr.', 'Ms.', 'Mrs.']):
                gender = doc.get('gender', '').lower()
                prefix = 'Ms. ' if gender == 'female' else 'Mr. '
                name = prefix + name
            
            quals = ', '.join([q.get('degree') for q in doc.get('qualifications', []) if q.get('degree')])
            exp_list = doc.get('experiences', [])
            position = exp_list[0].get('position', 'Psychologist') if exp_list else 'Psychologist'
            
            # Format signature details
            html = f"<strong>{name}</strong>"
            if quals:
                html += f",<br/>{quals}"
            if position:
                html += f"<br/>{position}"
            return html
    except Exception as e:
        traceback.print_exc()
    return ""


# ─── HTML builder ─────────────────────────────────────────────────────────────

def build_report_html(record: dict) -> str:
    """Return a complete A4 HTML document for the psychological report."""
    # Load defaults dynamically from MongoDB
    defaults = {}
    try:
        defaults_doc = db['milestone_backend_historyreport_defaultvalue'].find_one({"id": "psychological_report_defaults"})
        if defaults_doc:
            defaults = defaults_doc
    except Exception as e:
        print(f"Error fetching defaults from DB: {e}")

    id_data    = record.get('identification_data',        {})
    demo       = record.get('demographic_data',           {})
    hist       = record.get('history_of_present_illness', {})
    family     = record.get('family_history',             {})
    personal   = record.get('personal_history',           {})
    natal      = record.get('natalandneanatal_history',   {})
    postnatal  = record.get('postnatal_history',          {})
    dev_hist   = record.get('developmental_history',      {})
    scholastic = record.get('scholastic_history',         {})
    play       = record.get('play_history',               {})

    child_name = id_data.get('name', '–')
    informants = ', '.join(filter(None, [
        id_data.get('informant_a'), id_data.get('informant_b'),
    ]))
    dob_str    = id_data.get('dob', '')
    assess_str = id_data.get('date_of_assessment', '')

    # ── Prenatal defaults mapping
    prenatal_defaults = defaults.get('prenatal_defaults', {})
    prenatal  = personal.get('prenatal', {})
    pre_parts = []
    if prenatal.get('prenatal_history') == 'No':
        pre_parts.append(prenatal_defaults.get('prenatal_history_No', 'No significant prenatal history.'))
    if prenatal.get('reaction_towards_pregnancy'):
        pre_parts.append(f"Pregnancy was {prenatal['reaction_towards_pregnancy'].lower()}.")
    mh = prenatal.get('mother_health_during_pregnancy', {})
    if isinstance(mh, dict) and mh.get('is_any_issue') == 'No':
        pre_parts.append(prenatal_defaults.get('mother_health_No', "Mother's health during pregnancy was uneventful."))
    meds = prenatal.get('medications_used_during_pregnancy', '')
    if meds and meds != 'None':
        pre_parts.append(f"Medications: {meds}.")
    else:
        meds_default = prenatal_defaults.get('medications_None')
        if meds_default:
            pre_parts.append(meds_default)
            
    # Process any extra fields in prenatal dynamically
    processed_prenatal_keys = {
        'prenatal_history', 'conceptual_age_of_mother', 'reaction_towards_pregnancy',
        'abortion_attempt', 'mother_health_during_pregnancy', 'medications_used_during_pregnancy',
        'other_complaints'
    }
    for k, val in prenatal.items():
        if k not in processed_prenatal_keys and isinstance(val, str) and val.strip():
            pre_parts.append(f"{_fmt_key(k)}: {val.strip()}.")
            
    prenatal_text = ' '.join(pre_parts) or prenatal_defaults.get('prenatal_history_No', 'No significant prenatal history.')

    # ── Natal
    nat_parts = []
    if natal.get('term'):             nat_parts.append(f"Born at {natal['term'].lower()} term.")
    if natal.get('delivery_place'):   nat_parts.append(f"Delivery at {natal['delivery_place']}.")
    if natal.get('type_of_delivery'): nat_parts.append(f"{natal['type_of_delivery']} delivery.")
    if natal.get('birth_weight'):     nat_parts.append(f"Birth weight: {natal['birth_weight']}.")
    if natal.get('birth_cry'):        nat_parts.append(f"Birth cry: {natal['birth_cry'].lower()}.")
    
    # Process any extra fields in natal dynamically
    processed_natal_keys = {'term', 'delivery_place', 'type_of_delivery', 'birth_weight', 'birth_cry', 'caesarean_reason'}
    for k, val in natal.items():
        if k not in processed_natal_keys and isinstance(val, str) and val.strip():
            nat_parts.append(f"{_fmt_key(k)}: {val.strip()}.")
            
    natal_text = ' '.join(nat_parts) or '–'

    # ── Postnatal defaults mapping
    postnatal_defaults = defaults.get('postnatal_defaults', {})
    empty_postnatal = postnatal_defaults.get('empty_conditions', 'No significant postnatal complications.')
    conds = postnatal.get('selected_conditions', [])
    
    post_parts = []
    if conds:
        post_parts.append(', '.join(conds))
    elif postnatal.get('other_details'):
        post_parts.append(postnatal.get('other_details'))
        
    # Process any extra fields in postnatal dynamically
    processed_postnatal_keys = {'selected_conditions', 'other_details'}
    for k, val in postnatal.items():
        if k not in processed_postnatal_keys and isinstance(val, str) and val.strip():
            post_parts.append(f"{_fmt_key(k)}: {val.strip()}.")
            
    postnatal_text = ' '.join(post_parts) or empty_postnatal

    # ── Family defaults mapping
    family_defaults = defaults.get('family_history', {})
    cons_map = family_defaults.get('consanguinity_text', {})
    cons_val = family.get('consanguinity', 'No')
    consanguinity = cons_map.get(
        cons_val,
        'The child is born out of non-consanguineous parents.' if cons_val == 'No' else 'The child is born out of consanguineous parents.'
    )
    fam_parts = [consanguinity]
    
    fam_type_val = family.get('type_of_family', [])
    fam_type = '/'.join(fam_type_val) if fam_type_val else family_defaults.get('type_of_family', '')
    if fam_type:
        fam_parts.append(f"The family is a {fam_type.lower()} family.")
    if demo.get('father'):
        fam_parts.append(
            f"Father: {demo['father']}"
            f"{', ' + demo['father_occupation'] if demo.get('father_occupation') else ''}."
        )
    if demo.get('mother'):
        fam_parts.append(
            f"Mother: {demo['mother']}"
            f"{', ' + demo['mother_occupation'] if demo.get('mother_occupation') else ''}."
        )
    mh_fam = family.get('mental_medical_history', {})
    if isinstance(mh_fam, dict):
        if mh_fam.get('selected') == 'No':
            mmh_map = family_defaults.get('mental_medical_history', {})
            fam_parts.append(mmh_map.get('No', 'No significant family history of intellectual disability and mental illness.'))
        elif mh_fam.get('details'):
            fam_parts.append(f"Family history: {mh_fam['details']}.")
            
    # Process any extra fields in family dynamically
    processed_family_keys = {'consanguinity', 'type_of_family', 'family_genogram', 'mental_medical_history'}
    for k, val in family.items():
        if k not in processed_family_keys and isinstance(val, str) and val.strip():
            fam_parts.append(f"{_fmt_key(k)}: {val.strip()}.")
    family_text = ' '.join(fam_parts)

    # ── School defaults mapping
    school_defaults = defaults.get('school_history', {})
    school_status = scholastic.get('school_status')
    school_parts = []
    if school_status == 'Not yet started school':
        school_parts.append(school_defaults.get('Not yet started school', 'The child has not yet started school.'))
    else:
        main_sch_parts = [scholastic.get('type_of_school'), scholastic.get('present_class'), scholastic.get('scholastic_performance')]
        main_sch_str = ', '.join(filter(None, main_sch_parts))
        if main_sch_str:
            school_parts.append(main_sch_str)
        elif school_status:
            school_parts.append(school_status)
            
    # Process any extra fields in scholastic dynamically
    processed_school_keys = {
        'school_status', 'type_of_school', 'age_of_entry', 'present_class', 'medium_of_instruction',
        'scholastic_performance', 'disciplinary_problems', 'regularity', 'peer_group_adjustment',
        'relation_with_authorities', 'other_info'
    }
    for k, val in scholastic.items():
        if k not in processed_school_keys and isinstance(val, str) and val.strip():
            school_parts.append(f"{_fmt_key(k)}: {val.strip()}.")
    school_text = ' '.join(school_parts) or '–'

    # ── Play defaults mapping
    play_defaults = defaults.get('play_history', {})
    play_beh = play.get('play_behaviour')
    play_beh_text = play_defaults.get(play_beh, f"Play behaviour: {play_beh}.") if play_beh else ''
    
    play_pref = play.get('play_preferences')
    play_pref_text = play_defaults.get(play_pref, play_pref) if play_pref else ''
    
    screen_val = play.get('screen_time')
    screen_text = f"Screen time: {screen_val}." if screen_val else ''
    if screen_val and screen_val.lower() not in ['none', '0', 'no', 'nil'] and play_defaults.get('screen_time_delay'):
        screen_text += f" {play_defaults['screen_time_delay']}"

    play_parts = [
        play_beh_text,
        play_pref_text,
        play.get('group_behaviour', ''),
        screen_text,
        f"Sleep: {play['sleep_history']}."       if play.get('sleep_history') else '',
    ]
    
    # Process any extra fields in play dynamically
    processed_play_keys = {
        'play_behaviour', 'play_preferences', 'rule_knowledge', 'group_behaviour', 'leisure_time',
        'likes', 'dislikes', 'medical_history', 'sleep_history', 'allergy_history', 'screen_time'
    }
    for k, val in play.items():
        if k not in processed_play_keys and isinstance(val, str) and val.strip():
            play_parts.append(f"{_fmt_key(k)}: {val.strip()}.")
    play_text = ' '.join(filter(None, play_parts)) or '–'

    # ── History of present illness defaults mapping
    hpi_defaults = defaults.get('history_of_present_illness', {})
    mode_val = hist.get('mode_of_onset')
    mode_str = ', '.join(mode_val) if mode_val else hpi_defaults.get('mode_of_onset', 'Insidious')
    course_val = hist.get('course_of_illness')
    course_str = ', '.join(course_val) if course_val else hpi_defaults.get('course_of_illness', 'Continuous')
    prog_val = hist.get('progress')
    prog_str = ', '.join(prog_val) if prog_val else hpi_defaults.get('progress', 'Static')

    illness_parts = [
        f"Mode of onset: {mode_str}." if mode_str else '',
        f"Course: {course_str}." if course_str else '',
        f"Progress: {prog_str}." if prog_str else '',
    ]
    
    # Process any extra fields in history of present illness dynamically
    processed_hist_keys = {'mode_of_onset', 'course_of_illness', 'progress'}
    for k, val in hist.items():
        if k not in processed_hist_keys and isinstance(val, str) and val.strip():
            illness_parts.append(f"{_fmt_key(k)}: {val.strip()}.")
    illness_text = ' '.join(filter(None, illness_parts)) or '–'

    # ── Developmental tables
    gross_motor = dev_hist.get('gross_motor', [])
    language    = dev_hist.get('language',    [])
    fine_motor  = dev_hist.get('fine_motor',  [])
    social      = dev_hist.get('social',      [])
    main_rows   = gross_motor + language

    # ── Developmental rules / delay notes evaluation
    dev_rules = defaults.get('development_rules', {})
    rule_notes = []
    
    lang_rules = dev_rules.get('language_delay', {})
    has_lang_delayed = any(r.get('impression') == 'Delayed' for r in language)
    has_lang_not = any(r.get('impression') == 'Not Achieved' for r in language)
    if has_lang_delayed and 'Delayed' in lang_rules:
        rule_notes.append(lang_rules['Delayed'])
    if has_lang_not and 'Not Achieved' in lang_rules:
        rule_notes.append(lang_rules['Not Achieved'])
        
    soc_rules = dev_rules.get('social_delay', {})
    has_soc_not = any(r.get('impression') == 'Not Achieved' for r in social)
    if has_soc_not and 'Not Achieved' in soc_rules:
        rule_notes.append(soc_rules['Not Achieved'])

    dev_rows_html = ''.join(
        f'<tr><td style="text-align:center">{i+1}</td><td>{r.get("skill","")}</td>'
        f'<td style="text-align:center">{r.get("expected","")}</td>'
        f'<td style="text-align:center">{r.get("achieved","")}</td>'
        f'<td style="text-align:center;color:{_imp_color(r.get("impression",""))};font-weight:bold">'
        f'{r.get("impression","")}</td></tr>'
        for i, r in enumerate(main_rows)
    )

    max_split       = max(len(fine_motor), len(social), 1)
    split_rows_html = ''
    for i in range(max_split):
        fm  = fine_motor[i] if i < len(fine_motor) else {}
        soc = social[i]     if i < len(social)     else {}
        split_rows_html += (
            f'<tr><td>{fm.get("skill","")}</td>'
            f'<td style="text-align:center">{fm.get("expected","")}</td>'
            f'<td style="text-align:center;color:{_imp_color(fm.get("impression",""))};font-weight:bold">'
            f'{fm.get("impression","")}</td>'
            f'<td style="border-left:2px solid #555">{soc.get("skill","")}</td>'
            f'<td style="text-align:center">{soc.get("expected","")}</td>'
            f'<td style="text-align:center;color:{_imp_color(soc.get("impression",""))};font-weight:bold">'
            f'{soc.get("impression","")}</td></tr>'
        )


    complaints_html = ''.join(
        f'<li>{c}</li>' for c in record.get('presenting_complaints', [])
    )
    rec_html = ''.join(
        f'<li>{r.strip()}</li>'
        for r in record.get('Recommendation', '').split(',')
        if r.strip()
    )

    # Append rule notes (if any) to the overall impression
    overall_impression = record.get("OverAllImpression", "–")
    if rule_notes:
        notes_str = " ".join(rule_notes)
        if overall_impression and overall_impression != "–" and overall_impression != "&ndash;":
            overall_impression = f"{overall_impression} {notes_str}"
        else:
            overall_impression = notes_str

    creator_sig = _get_creator_signature(record.get('created_by'))
    if creator_sig:
        footer_html = f"""
        <div class="footer">
          <div class="footer-inner">
            <div style="float: left; width: 45%; font-size: 10pt;">
              <strong>Dr. D. Priyadharshni</strong><br/>
              Dch, DNB (pead)<br/>Paediatrician and play therapist<br/>Milestones Developmental Center
            </div>
            <div style="float: right; width: 45%; font-size: 10pt;">
              {creator_sig}
            </div>
            <div style="clear: both;"></div>
          </div>
        </div>
        """
    else:
        footer_defaults = defaults.get('report_footer', {})
        reported_by = footer_defaults.get('reported_by', [])
        if reported_by:
            footer_cols_html = ""
            for i, person in enumerate(reported_by):
                name = person.get('name', '')
                role = person.get('role', '')
                details = person.get('details', '')
                
                details_html = f"{role}"
                if details:
                    details_html += f"<br/>{details}"
                else:
                    clinic_name = footer_defaults.get('clinic', 'Milestones Developmental Center')
                    details_html += f"<br/>{clinic_name}"
                
                float_side = "left" if i % 2 == 0 else "right"
                footer_cols_html += f"""
                <div style="float: {float_side}; width: 45%; font-size: 10pt;">
                    <strong>{name}</strong><br/>
                    {details_html}
                </div>
                """
            footer_html = f"""
            <div class="footer">
              <div class="footer-inner">
                {footer_cols_html}
                <div style="clear: both;"></div>
              </div>
            </div>
            """
        else:
            footer_html = """
            <div class="footer">
              <div class="footer-inner">
                <div class="footer-left">
                  <strong>Dr. D. Priyadharshni</strong><br/>
                  Dch, DNB (pead)<br/>Paediatrician and play therapist<br/>Milestones Developmental Center
                </div>
                <div class="footer-right">
                  <strong>Ms. K. Devika,</strong><br/>
                  Clinical Psychologist,<br/>Special Educator for Autism Child<br/>MDC
                </div>
              </div>
            </div>
            """

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"/>
<style>
  @page {{ size: A4; margin: 18mm 20mm; }}
  body {{ font-family: Times New Roman, serif; font-size: 11pt; color: #000; }}
  .clinic-name {{ color: #2e7d32; font-size: 15pt; font-weight: bold; text-align: center;
                 text-transform: uppercase; letter-spacing: 1px; }}
  .clinic-addr {{ font-size: 8.5pt; text-align: center; color: #333; margin: 2px 0; }}
  .report-title {{ text-align: center; font-size: 13pt; font-weight: bold;
                  text-decoration: underline; text-transform: uppercase; margin: 8px 0 12px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 6px 0; }}
  .info-table td {{ border: 1px solid #555; padding: 4px 7px; font-size: 10.5pt; }}
  .dev-table th, .dev-table td {{ border: 1px solid #555; padding: 3px 5px; font-size: 9.5pt; }}
  .dev-table th {{ background: #e8f5e9; text-align: center; font-weight: bold; }}
  .split-table th, .split-table td {{ border: 1px solid #555; padding: 3px 5px; font-size: 9.5pt; }}
  .split-table th {{ background: #e8f5e9; text-align: center; font-weight: bold; }}
  .section-head {{ font-weight: bold; text-decoration: underline; font-size: 11pt; margin: 9px 0 3px; }}
  .bold {{ font-weight: bold; }}
  ul {{ margin-left: 18px; margin-bottom: 6px; }}
  ul li {{ margin-bottom: 2px; }}
  p {{ text-align: justify; margin-bottom: 5px; line-height: 1.5; }}
  .summary-box {{ border: 1px solid #aaa; padding: 8px; background: #f9fbe7; margin: 6px 0; }}
  .footer {{ margin-top: 28px; border-top: 1px solid #ccc; padding-top: 8px; }}
  .footer-inner {{ display: block; }}
  .footer-left  {{ float: left;  width: 45%; font-size: 10pt; }}
  .footer-right {{ float: right; width: 45%; font-size: 10pt; }}
</style>
</head>
<body>
  <div class="clinic-name">Milestones Developmental Center</div>
  <div class="clinic-addr">59 / 37, SARADHA COLLEGE ROAD, SALEM &ndash; 636007 &nbsp;|&nbsp; Ph: 9047033633</div>
  <div class="report-title">History Report</div>

  <table class="info-table">
    <tr>
      <td><span class="bold">Name:</span> {child_name}</td>
      <td><span class="bold">DOB:</span> {_fmt_date(dob_str)}</td>
      <td><span class="bold">Date of Evaluation:</span> {_fmt_date(assess_str)}</td>
    </tr>
    <tr>
      <td><span class="bold">Father:</span> {demo.get("father","&ndash;")}</td>
      <td><span class="bold">Age:</span> {_calc_age(dob_str, assess_str)}</td>
      <td><span class="bold">Reg. No.:</span> {record.get("registration_number","&ndash;")}</td>
    </tr>
    <tr>
      <td><span class="bold">Mother:</span> {demo.get("mother","&ndash;")}</td>
      <td><span class="bold">Mobile:</span> {demo.get("mobile_number","&ndash;")}</td>
      <td><span class="bold">Address:</span> {demo.get("address_city","&ndash;")}</td>
    </tr>
  </table>

  <p><span class="bold">Informant:</span> {informants or "&ndash;"} &nbsp;&nbsp;
     <span class="bold">Reliability:</span> {id_data.get("information_reliability","&ndash;")} &nbsp;&nbsp;
     <span class="bold">Adequacy:</span> {id_data.get("adequacy","&ndash;")}</p>

  <div class="section-head">Presenting Complaints:</div>
  <ul>{complaints_html}</ul>

  <div class="section-head">History of Present Illness:</div>
  <p>{illness_text}</p>

  <div class="section-head">Birth History and Developmental History:</div>
  <p>{consanguinity}</p>
  <p><span class="bold">Pre-natal:</span> {prenatal_text}</p>
  <p><span class="bold">Peri-natal:</span> {natal_text}</p>
  <p><span class="bold">Postnatal:</span> {postnatal_text}</p>

  <div class="section-head">Developmental History:</div>
  <table class="dev-table">
    <thead>
      <tr><th>S.No</th><th>Development (Gross Motor &amp; Language)</th>
          <th>Normal Dev.</th><th>Child Achieved</th><th>Impression</th></tr>
    </thead>
    <tbody>{dev_rows_html}</tbody>
  </table>

  <table class="split-table">
    <thead>
      <tr><th>Fine / Gross Motor</th><th>Expected</th><th>Impression</th>
          <th>Social</th><th>Expected</th><th>Impression</th></tr>
    </thead>
    <tbody>{split_rows_html}</tbody>
  </table>

  <p><span class="bold">Family history:</span> {family_text}</p>
  <p><span class="bold">School history:</span> {school_text}</p>
  <p><span class="bold">Play history:</span> {play_text}</p>
  <p><span class="bold">Treatment history:</span> {record.get("treatment_history","None")}</p>

  <div class="section-head">Summary:</div>
  <div class="summary-box"><p>{record.get("OverAllSummary","&ndash;")}</p></div>

  <p><span class="bold">Impression:</span> {overall_impression}</p>

  <div class="section-head">Recommendations:</div>
  <ul>{rec_html}</ul>

  <p style="text-align:center;margin-top:18px">Reported by</p>
  {footer_html}
</body>
</html>"""


# ─── API View ─────────────────────────────────────────────────────────────────

class HistorySheetPDFView(APIView):
    """
    Generate and stream a PDF for the psychological report.
    GET /history-sheet/pdf/?reg_no=MDC/230/2026
    """

    def get(self, request):
        from xhtml2pdf import pisa

        reg_no = request.query_params.get('reg_no')
        if not reg_no:
            return Response(
                {"error": "reg_no is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            collection = db['milestone_backend_historyrecordingsheet']
            record = collection.find_one({'registration_number': reg_no})
            if not record:
                return Response(
                    {"error": "History sheet not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            record['_id'] = str(record['_id'])
            record = clean_record(record)
            html_content = build_report_html(record)

            pdf_buffer = io.BytesIO()
            result = pisa.CreatePDF(io.StringIO(html_content), dest=pdf_buffer)

            if result.err:
                return Response(
                    {"error": "PDF generation failed"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            child_name = (
                record.get('identification_data', {})
                      .get('name', reg_no)
                      .replace(' ', '_')
            )
            filename = f"History_Report_{child_name}_{reg_no.replace('/', '-')}.pdf"

            pdf_buffer.seek(0)
            response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Access-Control-Expose-Headers'] = 'Content-Disposition'
            return response

        except Exception as e:
            traceback.print_exc()
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
