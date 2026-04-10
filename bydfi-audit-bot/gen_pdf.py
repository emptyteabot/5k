from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
import sqlite3
from datetime import datetime

DB = r"C:\repo\data\audit_records.sqlite3"
OUTPUT = r"C:\Users\cyh\Desktop\交易所实习\bydfi-audit-bot\data\reports\final_report_20260402.pdf"

conn = sqlite3.connect(DB)
c = conn.cursor()

blood_rows = c.execute("SELECT message_timestamp, reporter_name, source_title, substr(parsed_text, 1, 300) FROM audit_records WHERE source_title LIKE '%血战%' OR parsed_text LIKE '%血战%' ORDER BY message_timestamp DESC LIMIT 10").fetchall()
weekly_rows = c.execute("SELECT message_timestamp, reporter_name, source_title, substr(parsed_text, 1, 300) FROM audit_records WHERE source_title LIKE '%周报%' OR source_title LIKE '%会议%' ORDER BY message_timestamp DESC LIMIT 10").fetchall()
cex_rows = c.execute("SELECT message_timestamp, reporter_name, source_title, substr(parsed_text, 1, 300) FROM audit_records WHERE source_title LIKE '%CEX%' OR parsed_text LIKE '%CEX%' ORDER BY message_timestamp DESC LIMIT 10").fetchall()
conn.close()

doc = SimpleDocTemplate(OUTPUT, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
story = []
styles = getSampleStyleSheet()

title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=24, textColor=colors.HexColor('#1f4788'), spaceAfter=12, alignment=1)
story.append(Paragraph("BYDFi 执行审计报告", title_style))
story.append(Paragraph(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
story.append(Spacer(1, 0.3*inch))

story.append(Paragraph("一、血战到底进展", styles['Heading2']))
if blood_rows:
    data = [["时间", "上报人", "标题", "内容摘要"]]
    for row in blood_rows[:5]:
        data.append([row[0][:10] if row[0] else "", row[1][:12] if row[1] else "", row[2][:30] if row[2] else "", row[3][:60] if row[3] else ""])
    table = Table(data, colWidths=[1.2*inch, 1*inch, 1.5*inch, 1.3*inch])
    table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke), ('ALIGN', (0, 0), (-1, -1), 'LEFT'), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (-1, 0), 10), ('BOTTOMPADDING', (0, 0), (-1, 0), 12), ('BACKGROUND', (0, 1), (-1, -1), colors.beige), ('GRID', (0, 0), (-1, -1), 1, colors.black)]))
    story.append(table)
else:
    story.append(Paragraph("暂无血战到底相关记录", styles['Normal']))
story.append(Spacer(1, 0.2*inch))

story.append(Paragraph("二、周报系统与会议记录", styles['Heading2']))
if weekly_rows:
    data = [["时间", "上报人", "标题", "内容摘要"]]
    for row in weekly_rows[:5]:
        data.append([row[0][:10] if row[0] else "", row[1][:12] if row[1] else "", row[2][:30] if row[2] else "", row[3][:60] if row[3] else ""])
    table = Table(data, colWidths=[1.2*inch, 1*inch, 1.5*inch, 1.3*inch])
    table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke), ('ALIGN', (0, 0), (-1, -1), 'LEFT'), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (-1, 0), 10), ('BOTTOMPADDING', (0, 0), (-1, 0), 12), ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue), ('GRID', (0, 0), (-1, -1), 1, colors.black)]))
    story.append(table)
else:
    story.append(Paragraph("暂无周报相关记录", styles['Normal']))
story.append(Spacer(1, 0.2*inch))

story.append(Paragraph("三、CEX 进度与风险", styles['Heading2']))
if cex_rows:
    data = [["时间", "上报人", "标题", "内容摘要"]]
    for row in cex_rows[:5]:
        data.append([row[0][:10] if row[0] else "", row[1][:12] if row[1] else "", row[2][:30] if row[2] else "", row[3][:60] if row[3] else ""])
    table = Table(data, colWidths=[1.2*inch, 1*inch, 1.5*inch, 1.3*inch])
    table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke), ('ALIGN', (0, 0), (-1, -1), 'LEFT'), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (-1, 0), 10), ('BOTTOMPADDING', (0, 0), (-1, 0), 12), ('BACKGROUND', (0, 1), (-1, -1), colors.lightgreen), ('GRID', (0, 0), (-1, -1), 1, colors.black)]))
    story.append(table)
else:
    story.append(Paragraph("暂无 CEX 相关记录", styles['Normal']))

story.append(Spacer(1, 0.3*inch))
story.append(Paragraph("报告说明：本报告基于实时数据库生成，包含血战到底、周报系统、CEX 三大业务线最新进展。", styles['Normal']))

doc.build(story)
print(f"PDF generated: {OUTPUT}")
