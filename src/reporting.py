"""Create a concise report and vector charts with ReportLab."""
import math
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics import renderSVG, renderPDF

BLUE=colors.HexColor('#23485B')
TEAL=colors.HexColor('#248A8D')

def bar_chart(title,categories,series,maximum,units,legend=None):
    d=Drawing(490,250)
    d.add(String(12,234,title,fontName='Helvetica-Bold',fontSize=13,fillColor=BLUE))
    d.add(String(12,216,units,fontName='Helvetica',fontSize=9,fillColor=colors.HexColor('#586579')))
    chart=VerticalBarChart()
    chart.x=46;chart.y=38;chart.width=425;chart.height=155
    chart.data=series;chart.categoryAxis.categoryNames=categories
    chart.categoryAxis.labels.fontName='Helvetica';chart.categoryAxis.labels.fontSize=9
    chart.valueAxis.valueMin=0;chart.valueAxis.valueMax=maximum
    chart.valueAxis.valueStep=max(1,maximum/5)
    chart.valueAxis.labels.fontName='Helvetica';chart.valueAxis.labels.fontSize=9
    chart.bars[0].fillColor=BLUE
    if len(series)>1: chart.bars[1].fillColor=TEAL
    chart.strokeColor=None
    d.add(chart)
    if legend:
        key=Legend();key.x=300;key.y=214;key.fontName='Helvetica';key.fontSize=9
        key.colorNamePairs=[(BLUE,legend[0]),(TEAL,legend[1])];key.columnMaximum=1
        d.add(key)
    return d

def make_report(root,overall,grouped,audit,bounds):
    sorted_rates=overall.sort_values('MissingRate',ascending=False)
    rate_chart=bar_chart('Missing measurements by biomarker',sorted_rates.Biomarker.tolist(),
                         [(sorted_rates.MissingRate*100).tolist()],10,'Unweighted adult sample. Missing values (%)')
    order=['20-39','40-59','60-79','80+']
    alt=grouped.loc[grouped.Biomarker.eq('ALT')]
    values=[[float(alt.loc[alt.SexLabel.eq(sex)&alt.AgeBand.eq(age),'Median'].iloc[0]) for age in order] for sex in ['Female','Male']]
    alt_chart=bar_chart('ALT medians by age and recorded sex',order,values,
                        math.ceil(max(max(v) for v in values)/10)*10,'Observed ALT (U/L). Unweighted; missing observations excluded from medians.', ['Female','Male'])
    for name,figure in [('missingness',rate_chart),('alt_medians',alt_chart)]:
        renderSVG.drawToFile(figure,str(root/'reports/figures'/f'{name}.svg'))
        renderPDF.drawToFile(figure,str(root/'reports/figures'/f'{name}.pdf'))
    styles=getSampleStyleSheet()
    styles['Normal'].fontSize=10;styles['Normal'].leading=14;styles['Normal'].spaceAfter=8
    styles['Title'].textColor=BLUE;styles['Heading2'].textColor=TEAL
    story=[]
    def p(text,style='Normal'):story.append(Paragraph(text,styles[style]))
    def table(rows,widths):
        t=Table(rows,colWidths=widths,repeatRows=1)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),BLUE),('TEXTCOLOR',(0,0),(-1,0),colors.white),
            ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),9),
            ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#EFF4F7'),colors.white]),
            ('ALIGN',(1,1),(-1,-1),'RIGHT')]))
        story.append(t);story.append(Spacer(1,12))
    p('Real biomedical data,<br/>reproducible analysis','Title')
    p('NHANES 2017-2018 | Excel, Power Query and SQLite | 7 October 2026')
    p('Question','Heading2')
    p('How do data availability and the distributions of six liver and kidney biomarkers vary by age and recorded sex in the adult NHANES sample?')
    p('Cohort and transformations','Heading2')
    p(f'The biochemistry file contains {audit["source_biochemistry_rows"]:,} records. A checked one-to-one participant-ID join matches every laboratory record to demographics. Restricting to age 20 and older retains {audit["adult_rows"]:,} adults and excludes {audit["excluded_under_20"]:,} records. Reshaping six biomarkers produces {audit["long_rows"]:,} measurement slots, including missing values.')
    table([['Checkpoint','Count'],['Laboratory records',f'{audit["joined_rows"]:,}'],['Adults aged 20+',f'{audit["adult_rows"]:,}'],['Observed measurements',f'{audit["observed_measurements"]:,}'],['Missing measurement slots',f'{audit["missing_measurements"]:,}'],['Imputed values / removed outliers','0 / 0']],[310,160])
    p('Cleaning decisions','Heading2')
    p('Preserve the original XPT files and published measurement units. Normalize decoder artifacts only in source code/weight fields. Decode source-recorded sex and retain the 80+ age category. Preserve ALT/GGT detection-limit flags. Use a pooled adult 1.5-IQR rule to mark values for statistical review. No flagged measurements are removed or classified as clinical abnormalities.')
    p('Scope','Heading2')
    p('All results describe the included sample without survey weighting. They are not US population estimates, causal findings or diagnoses. Survey weights, strata and primary sampling-unit fields remain available for later design-aware work.')
    story.append(PageBreak())
    p('Availability and distributions','Title')
    story.append(rate_chart)
    table([['Biomarker','Observed','Missing','Missing %'],*[[r.Biomarker,f'{r.Observed:,}',f'{r.Missing:,}',f'{100*r.MissingRate:.2f}%'] for r in sorted_rates.itertuples()]],[170,100,100,100])
    p('Interpretation','Heading2')
    highest=sorted_rates.iloc[0];lowest=sorted_rates.iloc[-1]
    p(f'Adult-sample missingness ranges from {100*lowest.MissingRate:.2f}% for {lowest.Biomarker} to {100*highest.MissingRate:.2f}% for {highest.Biomarker}. The six biomarker-specific denominators are all {audit["adult_rows"]:,}, because the long-form transformation retains missing slots. Differences in availability should be assessed before complete-case analysis or imputation.')
    p('Counts matter','Heading2')
    p('The grouped CSV includes the participant, observed and missing counts for every biomarker, age band and recorded-sex group. Medians and means exclude missing values. Do not average measurements across biomarkers with different units.')
    story.append(PageBreak())
    p('Audit and reproducibility','Title')
    story.append(alt_chart)
    p('Cross-tool checks','Heading2')
    p(f'SQL JOIN/CTE/UNION ALL views independently reconstruct the cohort and long format. SQL window functions calculate group medians. The pipeline reconciles all {audit["long_rows_compared"]:,} long-form records and {audit["group_rows_compared"]} group summaries against these SQL results. SQLite integrity and foreign-key checks pass. CSV exports are read back and compared to their source frames.')
    p('Excel verification status','Heading2')
    p('The native review workbook opened, recalculated, saved and reopened in desktop Excel. Six formula summaries and the age/sex selector results matched the verified data for ALT and Creatinine. Both charts persisted. Power Query opened, but editor text input through app control failed; script activation also returned access denied. Query refresh, PivotTables and slicers remain pending. Their M queries and completion script are supplied, with verification status documented.')
    p('Source and authorship','Heading2')
    p('Source: CDC, National Center for Health Statistics. National Health and Nutrition Examination Survey, 2017-2018, Standard Biochemistry Profile and Demographics. Public-use data retrieved 7 October 2026. Source file hashes are pinned in the pipeline. This is an AI-assisted portfolio project; contributions and verification status are documented in the repository.')
    for title,url in [('CDC biochemistry codebook','https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/BIOPRO_J.htm'),('CDC demographics codebook','https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/DEMO_J.htm')]:
        p(f'<link href="{url}" color="#248A8D">{title}</link>')
    def footer(canvas,doc):
        canvas.setFont('Helvetica',9);canvas.setFillColor(colors.HexColor('#586579'))
        canvas.drawString(42,24,'NHANES 2017-2018 | Unweighted adult sample')
        canvas.drawRightString(A4[0]-42,24,str(doc.page))
    SimpleDocTemplate(str(root/'reports/NHANES_analysis.pdf'),pagesize=A4,leftMargin=42,rightMargin=42,topMargin=38,bottomMargin=42).build(story,onFirstPage=footer,onLaterPages=footer)
