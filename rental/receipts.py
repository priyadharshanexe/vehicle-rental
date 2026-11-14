"""Printable rental summary using the booked price snapshot, never current rates."""
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


def render_booking_summary(stream, booking):
    ink = colors.HexColor('#232735')
    purple = colors.HexColor('#5b43cf')
    muted = colors.HexColor('#777383')
    line = colors.HexColor('#e8e5ef')
    styles = {
        'body': ParagraphStyle('body', fontName='Helvetica', fontSize=10, leading=16, textColor=ink),
        'muted': ParagraphStyle('muted', fontName='Helvetica', fontSize=9, leading=14, textColor=muted),
        'title': ParagraphStyle('title', fontName='Helvetica-Bold', fontSize=28, leading=34, textColor=ink),
        'heading': ParagraphStyle('heading', fontName='Helvetica-Bold', fontSize=13, leading=20, textColor=ink),
        'amount': ParagraphStyle('amount', fontName='Helvetica-Bold', fontSize=17, leading=24, textColor=purple, alignment=TA_RIGHT),
        'right': ParagraphStyle('right', fontName='Helvetica', fontSize=10, leading=16, textColor=ink, alignment=TA_RIGHT),
    }
    def text(value, style='body'):
        return Paragraph(escape(str(value or 'Not provided')), styles[style])
    def currency(value):
        return f'INR {value:,.2f}'
    doc = SimpleDocTemplate(stream, pagesize=A4, rightMargin=48, leftMargin=48,
                            topMargin=90, bottomMargin=64, title='Motorlane | Booking summary')
    width = A4[0] - 96
    rows = [text('Your rental summary', 'title'), Spacer(1, 10),
            text('A record of your reservation and booked rental price.', 'muted'), Spacer(1, 28),
            text(booking.vehicle.name, 'heading'),
            text(f'{booking.vehicle.vehicle_type} / {booking.vehicle.location or "Location to be arranged"}', 'muted'),
            Spacer(1, 20)]
    details = Table([
        [text('RENTER', 'muted'), text('RENTAL STATUS', 'muted')],
        [text(booking.contact_name or booking.user.name), text(booking.display_status)],
        [text('PICKUP', 'muted'), text('RETURN', 'muted')],
        [text(booking.start_date.strftime('%d %b %Y')), text(booking.end_date.strftime('%d %b %Y'))],
    ], colWidths=[width/2]*2)
    details.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#f7f6fa')),
                                ('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10),
                                ('LEFTPADDING',(0,0),(-1,-1),16),('VALIGN',(0,0),(-1,-1),'TOP')]))
    rows += [details, Spacer(1, 28), text('Price breakdown', 'heading'), Spacer(1, 10)]
    costs = []
    if booking.quoted_daily_rate is not None:
        costs.append([text('Booked daily rate'), text(currency(booking.quoted_daily_rate), 'right')])
    costs += [[text('Rental duration'), text(f'{booking.days} days', 'right')],
              [text('Booking total', 'heading'), text(currency(booking.total_price), 'amount')]]
    pricing = Table(costs, colWidths=[width*.6,width*.4])
    pricing.setStyle(TableStyle([('LINEBELOW',(0,0),(-1,-2),.5,line),
                                ('TOPPADDING',(0,0),(-1,-1),14),('BOTTOMPADDING',(0,0),(-1,-1),14),
                                ('BACKGROUND',(0,-1),(-1,-1),colors.HexColor('#f0ecfa')),
                                ('LEFTPADDING',(0,0),(-1,-1),14),('RIGHTPADDING',(0,0),(-1,-1),14),
                                ('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
    rows += [pricing, Spacer(1, 12), text('Both pickup and return dates are included in the rental duration.', 'muted'),
             Spacer(1, 28), text('Before your trip', 'heading'),
             text('Arrange the exact pickup point and handoff with the vehicle owner. A pending request is not a confirmed reservation.', 'muted'),
             Spacer(1, 12), text('This is a booking summary, not a payment receipt or tax invoice. Motorlane has not collected a payment for this reservation.', 'muted')]
    if booking.pickup_notes:
        rows += [Spacer(1, 24), text('Your pickup notes', 'heading'), text(booking.pickup_notes)]
    def frame(canvas, document):
        canvas.saveState()
        canvas.setFillColor(purple);canvas.setFont('Helvetica-Bold',17);canvas.drawString(48,A4[1]-48,'Motorlane')
        canvas.setStrokeColor(line);canvas.line(48,A4[1]-64,A4[0]-48,A4[1]-64)
        canvas.setFillColor(muted);canvas.setFont('Helvetica',8)
        canvas.drawString(48,35,'Local rides. New possibilities.')
        canvas.drawRightString(A4[0]-48,35,f'Booking summary / {document.page}')
        canvas.restoreState()
    doc.build(rows,onFirstPage=frame,onLaterPages=frame)
