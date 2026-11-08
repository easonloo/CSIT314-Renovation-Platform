from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from accounts.decorators import platform_manager_required

from .controllers import InvalidReportPeriod, get_report_controller


def _pdf_escape(value):
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _create_report_pdf(lines):
    commands = []
    y = 760
    for index, line in enumerate(lines):
        font_size = 16 if index == 0 else 11
        commands.append(
            f"BT /F1 {font_size} Tf 1 0 0 1 50 {y} Tm "
            f"({_pdf_escape(line)}) Tj ET"
        )
        y -= 30 if index == 0 else 24
    stream = "\n".join(commands).encode("ascii")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n"
        + stream
        + b"\nendstream",
    ]

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for object_number, object_content in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{object_number} 0 obj\n".encode("ascii"))
        pdf.extend(object_content)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (
            f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(pdf)


@platform_manager_required
@require_http_methods(["GET"])
def report(request, period="daily"):
    try:
        report_data = get_report_controller(period).get_report_data()
    except InvalidReportPeriod as error:
        raise Http404(str(error)) from error
    return render(
        request,
        "reports/report.html",
        {"report": report_data, "period": period},
    )


@platform_manager_required
@require_http_methods(["GET"])
def report_download(request, period="daily"):
    try:
        report_data = get_report_controller(period).get_report_data()
    except InvalidReportPeriod as error:
        raise Http404(str(error)) from error
    generated_at = timezone.localtime(timezone.now()).strftime(
        "%d %b %Y, %H:%M:%S %Z"
    )
    lines = [
        f"{period.title()} Platform Report",
        (
            f"Report dates: {report_data['start_date']:%d %b %Y} to "
            f"{report_data['end_date']:%d %b %Y}"
        ),
        f"Generated: {generated_at}",
        "",
        f"New users: {report_data['new_users']}",
        f"IDP views: {report_data['views']}",
        f"Shortlists: {report_data['shortlists']}",
        f"New projects: {report_data['new_projects']}",
        f"Active users: {report_data['active_users']}",
        f"Total IDPs: {report_data['total_projects']}",
    ]
    response = HttpResponse(
        _create_report_pdf(lines),
        content_type="application/pdf",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="platform-{period}-report-'
        f'{report_data["start_date"]:%Y-%m-%d}.pdf"'
    )
    return response
