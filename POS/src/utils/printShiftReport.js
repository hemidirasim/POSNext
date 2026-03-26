import { call } from "@/utils/apiWrapper"
import { logger } from "@/utils/logger"
import { printHTML as qzPrintHTML } from "@/utils/qzTray"

const log = logger.create("PrintShiftReport")

// ============================================================================
// Shift Report Printing - X Report & Z Report
// ============================================================================

/**
 * Format currency amount
 */
function formatCurrency(amount) {
	return Number.parseFloat(amount || 0).toFixed(2)
}

/**
 * Format date for receipt
 */
function formatDate(dateStr) {
	if (!dateStr) return ""
	const date = new Date(dateStr)
	return date.toLocaleDateString("az-AZ", {
		day: "2-digit",
		month: "2-digit",
		year: "numeric",
	})
}

/**
 * Format time for receipt
 */
function formatTime(dateStr) {
	if (!dateStr) return ""
	const date = new Date(dateStr)
	return date.toLocaleTimeString("az-AZ", {
		hour: "2-digit",
		minute: "2-digit",
	})
}

/**
 * Generate X Report HTML for thermal printer (80mm)
 */
export function generateXReportHTML(reportData) {
	const { shift_info, sales_summary, payments, tax_summary } = reportData
	
	const html = `
<!DOCTYPE html>
<html>
<head>
	<meta charset="UTF-8">
	<title>X Report</title>
	<style>
		* { margin: 0; padding: 0; box-sizing: border-box; }
		body {
			font-family: 'Courier New', monospace;
			width: 80mm;
			padding: 5mm;
			font-size: 12px;
			font-weight: bold;
			color: black;
		}
		.center { text-align: center; }
		.bold { font-weight: bold; }
		.large { font-size: 16px; }
		.xlarge { font-size: 20px; }
		.line {
			border-top: 1px dashed #000;
			margin: 8px 0;
		}
		.double-line {
			border-top: 2px solid #000;
			border-bottom: 2px solid #000;
			margin: 8px 0;
			padding: 4px 0;
		}
		.section { margin: 10px 0; }
		.row {
			display: flex;
			justify-content: space-between;
			margin: 4px 0;
		}
		.header {
			text-align: center;
			margin-bottom: 15px;
		}
		.header-title {
			font-size: 24px;
			font-weight: bold;
			margin-bottom: 5px;
		}
		.header-subtitle {
			font-size: 14px;
		}
		.shift-info {
			margin: 10px 0;
			padding: 8px;
			border: 1px dashed #000;
		}
		.sales-summary .amount {
			font-size: 14px;
		}
		.net-sales {
			font-size: 18px;
			padding: 5px 0;
		}
		.footer {
			text-align: center;
			margin-top: 20px;
			padding-top: 10px;
			border-top: 2px dashed #000;
		}
		.status-open {
			background: #e8f5e9;
			padding: 3px 8px;
			display: inline-block;
		}
		@media print {
			@page { size: 80mm auto; margin: 0; }
			body { width: 80mm; padding: 3mm; }
		}
	</style>
</head>
<body>
	<div class="header">
		<div class="header-title">*** ${__("shift.x_report_title")} ***</div>
		<div class="header-subtitle">${__("shift.x_report_subtitle")}</div>
	</div>

	<div class="shift-info">
		<div class="row">
			<span>${__("POS Profile:")}</span>
			<span>${shift_info.pos_profile}</span>
		</div>
		<div class="row">
			<span>${__("shift.cashier")}:</span>
			<span>${shift_info.cashier}</span>
		</div>
		<div class="row">
			<span>${__("shift.shift_started")}:</span>
			<span>${formatDate(shift_info.shift_start)} ${formatTime(shift_info.shift_start)}</span>
		</div>
		<div class="row">
			<span>${__("shift.report_time")}:</span>
			<span>${formatDate(shift_info.report_generated)} ${formatTime(shift_info.report_generated)}</span>
		</div>
		<div class="center" style="margin-top: 8px;">
			<span class="status-open">${__("shift.shift_open")}</span>
		</div>
	</div>

	<div class="double-line center">
		<div class="xlarge">${__("shift.sales_list")}</div>
	</div>

	<div class="section sales-summary">
		<div class="row">
			<span>${__("shift.gross_sales")}:</span>
			<span class="amount">${formatCurrency(sales_summary.gross_sales)}</span>
		</div>
		<div class="row">
			<span>${__("shift.discounts")}:</span>
			<span class="amount">-${formatCurrency(sales_summary.discounts)}</span>
		</div>
		<div class="row">
			<span>${__("shift.returns")}:</span>
			<span class="amount">-${formatCurrency(sales_summary.returns)}</span>
		</div>
		<div class="line"></div>
		<div class="row net-sales bold">
			<span>${__("shift.net_sales")}:</span>
			<span>${formatCurrency(sales_summary.net_sales)}</span>
		</div>
	</div>

	<div class="line"></div>

	<div class="section">
		<div class="center bold large" style="margin-bottom: 8px;">${__("shift.payment_methods")}</div>
		<div class="row">
			<span>${__("shift.cash")}:</span>
			<span>${formatCurrency(payments.cash)}</span>
		</div>
		<div class="row">
			<span>${__("shift.card")}:</span>
			<span>${formatCurrency(payments.card)}</span>
		</div>
		<div class="row">
			<span>${__("shift.other")}:</span>
			<span>${formatCurrency(payments.other)}</span>
		</div>
		<div class="line"></div>
		<div class="row bold">
			<span>${__("shift.total_payment")}:</span>
			<span>${formatCurrency(payments.total)}</span>
		</div>
	</div>

	<div class="line"></div>

	<div class="section">
		<div class="center bold large" style="margin-bottom: 8px;">${__("shift.tax_information")}</div>
		${tax_summary.length > 0 ? tax_summary.map(tax => `
		<div class="row">
			<span>${tax.account.split(" - ")[0]} (${tax.rate}%):</span>
			<span>${formatCurrency(tax.amount)}</span>
		</div>
		`).join("") : `
		<div class="row">
			<span>${__("shift.no_tax")}</span>
			<span>-</span>
		</div>
		`}
		<div class="line"></div>
		<div class="row bold">
			<span>${__("shift.total_tax")}:</span>
			<span>${formatCurrency(sales_summary.tax_collected)}</span>
		</div>
	</div>

	<div class="line"></div>

	<div class="section">
		<div class="center bold large" style="margin-bottom: 8px;">${__("shift.statistics")}</div>
		<div class="row">
			<span>${__("shift.invoice_count")}:</span>
			<span>${reportData.invoices.total_count}</span>
		</div>
		<div class="row">
			<span>${__("shift.average_ticket")}:</span>
			<span>${formatCurrency(reportData.invoices.total_count > 0 ? sales_summary.net_sales / reportData.invoices.total_count : 0)}</span>
		</div>
	</div>

	<div class="footer">
		<div class="line"></div>
		<div style="font-size: 10px;">${__("shift.x_report_footer")}</div>
		<div style="font-size: 10px; margin-top: 5px;">Powered by BrainWise</div>
	</div>
</body>
</html>`

	return html
}

/**
 * Generate Z Report HTML for thermal printer (80mm)
 */
export function generateZReportHTML(reportData) {
	const { shift_info, sales_summary, payments, tax_summary, statistics } = reportData
	
	const html = `
<!DOCTYPE html>
<html>
<head>
	<meta charset="UTF-8">
	<title>Z Report</title>
	<style>
		* { margin: 0; padding: 0; box-sizing: border-box; }
		body {
			font-family: 'Courier New', monospace;
			width: 80mm;
			padding: 5mm;
			font-size: 12px;
			font-weight: bold;
			color: black;
		}
		.center { text-align: center; }
		.bold { font-weight: bold; }
		.large { font-size: 14px; }
		.xlarge { font-size: 22px; }
		.line {
			border-top: 1px dashed #000;
			margin: 8px 0;
		}
		.double-line {
			border-top: 2px solid #000;
			border-bottom: 2px solid #000;
			margin: 8px 0;
			padding: 4px 0;
		}
		.section { margin: 10px 0; }
		.row {
			display: flex;
			justify-content: space-between;
			margin: 4px 0;
		}
		.header {
			text-align: center;
			margin-bottom: 15px;
		}
		.header-title {
			font-size: 28px;
			font-weight: bold;
			margin-bottom: 5px;
		}
		.header-subtitle {
			font-size: 14px;
		}
		.shift-info {
			margin: 10px 0;
			padding: 8px;
			border: 2px solid #000;
		}
		.final-box {
			border: 3px double #000;
			padding: 10px;
			margin: 10px 0;
		}
		.net-sales {
			font-size: 20px;
			padding: 5px 0;
		}
		.footer {
			text-align: center;
			margin-top: 20px;
			padding-top: 10px;
			border-top: 2px dashed #000;
		}
		.status-closing {
			background: #ffebee;
			padding: 3px 8px;
			display: inline-block;
		}
		.asterisks {
			font-size: 24px;
			letter-spacing: 3px;
		}
		@media print {
			@page { size: 80mm auto; margin: 0; }
			body { width: 80mm; padding: 3mm; }
		}
	</style>
</head>
<body>
	<div class="header">
		<div class="asterisks">*******</div>
		<div class="header-title">${__("shift.z_report_title")}</div>
		<div class="header-subtitle">${__("shift.z_report_subtitle")}</div>
		<div class="asterisks">*******</div>
	</div>

	<div class="shift-info">
		<div class="row">
			<span>${__("POS Profile:")}</span>
			<span>${shift_info.pos_profile}</span>
		</div>
		<div class="row">
			<span>${__("shift.cashier")}:</span>
			<span>${shift_info.cashier}</span>
		</div>
		<div class="line"></div>
		<div class="row">
			<span>${__("shift.shift_started")}:</span>
			<span>${formatDate(shift_info.shift_start)} ${formatTime(shift_info.shift_start)}</span>
		</div>
		<div class="row">
			<span>${__("shift.shift_end")}:</span>
			<span>${formatDate(shift_info.shift_end)} ${formatTime(shift_info.shift_end)}</span>
		</div>
		<div class="row bold">
			<span>${__("shift.duration")}:</span>
			<span>${shift_info.duration?.formatted || "-"}</span>
		</div>
		<div class="center" style="margin-top: 8px;">
			<span class="status-closing">${__("shift.shift_closing")}</span>
		</div>
	</div>

	<div class="final-box">
		<div class="center xlarge bold" style="margin-bottom: 10px;">
			${__("shift.end_of_day")}
		</div>
		<div class="row">
			<span>${__("shift.gross_sales")}:</span>
			<span>${formatCurrency(sales_summary.gross_sales)}</span>
		</div>
		<div class="row">
			<span>${__("shift.discounts")}:</span>
			<span>-${formatCurrency(sales_summary.discounts)}</span>
		</div>
		<div class="row">
			<span>${__("shift.returns")}:</span>
			<span>-${formatCurrency(sales_summary.returns)}</span>
		</div>
		<div class="line"></div>
		<div class="row net-sales bold">
			<span>${__("shift.net_sales")}:</span>
			<span>${formatCurrency(sales_summary.net_sales)}</span>
		</div>
	</div>

	<div class="line"></div>

	<div class="section">
		<div class="center bold large" style="margin-bottom: 8px;">${__("shift.payment_methods")}</div>
		<div class="row">
			<span>${__("shift.cash")}:</span>
			<span>${formatCurrency(payments.cash)}</span>
		</div>
		<div class="row">
			<span>${__("shift.card")}:</span>
			<span>${formatCurrency(payments.card)}</span>
		</div>
		<div class="row">
			<span>${__("shift.other")}:</span>
			<span>${formatCurrency(payments.other)}</span>
		</div>
		<div class="line"></div>
		<div class="row bold large">
			<span>${__("shift.total_payment_upper")}:</span>
			<span>${formatCurrency(payments.total)}</span>
		</div>
	</div>

	<div class="line"></div>

	<div class="section">
		<div class="center bold large" style="margin-bottom: 8px;">${__("shift.tax_information")}</div>
		${tax_summary.length > 0 ? tax_summary.map(tax => `
		<div class="row">
			<span>${tax.account.split(" - ")[0]} (${tax.rate}%):</span>
			<span>${formatCurrency(tax.amount)}</span>
		</div>
		`).join("") : `
		<div class="row">
			<span>${__("shift.no_tax")}</span>
			<span>-</span>
		</div>
		`}
		<div class="line"></div>
		<div class="row bold">
			<span>${__("shift.total_tax")}:</span>
			<span>${formatCurrency(sales_summary.tax_collected)}</span>
		</div>
	</div>

	<div class="line"></div>

	<div class="section">
		<div class="center bold large" style="margin-bottom: 8px;">${__("shift.statistics")}</div>
		<div class="row">
			<span>${__("shift.invoice_count")}:</span>
			<span>${statistics.invoices_count}</span>
		</div>
		<div class="row">
			<span>${__("shift.average_ticket")}:</span>
			<span>${formatCurrency(statistics.average_ticket)}</span>
		</div>
		<div class="row">
			<span>${__("shift.sales_per_hour")}:</span>
			<span>${statistics.invoices_per_hour?.toFixed(1) || 0}</span>
		</div>
	</div>

	<div class="double-line center" style="margin-top: 15px;">
		<div style="font-size: 16px;">${__("shift.shift_closed")}</div>
	</div>

	<div class="footer">
		<div class="line"></div>
		<div style="font-size: 10px;">${__("shift.z_report_footer")}</div>
		<div style="font-size: 10px; margin-top: 5px;">Powered by BrainWise</div>
	</div>
</body>
</html>`

	return html
}

/**
 * Print X Report (mid-shift report)
 */
export async function printXReport(posProfile, openingShift = null) {
	try {
		log.info("Generating X Report...")
		
		// Get report data from server
		const reportData = await call("pos_next.api.shift_reports.print_x_report", {
			pos_profile: posProfile,
			opening_shift: openingShift,
		})
		
		// Generate HTML
		const html = generateXReportHTML(reportData)
		
		// Try silent print first, then browser print
		try {
			await qzPrintHTML(html)
			log.info("X Report printed silently")
			return { success: true, method: "silent" }
		} catch (silentError) {
			log.warn("Silent print failed, using browser print:", silentError)
			
			// Open in new window for browser print
			const printWindow = window.open("", "_blank", "width=350,height=600")
			printWindow.document.write(html)
			printWindow.document.close()
			printWindow.onload = () => {
				setTimeout(() => printWindow.print(), 250)
			}
			
			return { success: true, method: "browser" }
		}
	} catch (error) {
		log.error("Failed to print X Report:", error)
		throw error
	}
}

/**
 * Print Z Report (end-of-shift report)
 */
export async function printZReport(posProfile, openingShift = null) {
	try {
		log.info("Generating Z Report...")
		
		// Get report data from server
		const reportData = await call("pos_next.api.shift_reports.print_z_report", {
			pos_profile: posProfile,
			opening_shift: openingShift,
		})
		
		// Generate HTML
		const html = generateZReportHTML(reportData)
		
		// Try silent print first, then browser print
		try {
			await qzPrintHTML(html)
			log.info("Z Report printed silently")
			return { success: true, method: "silent" }
		} catch (silentError) {
			log.warn("Silent print failed, using browser print:", silentError)
			
			// Open in new window for browser print
			const printWindow = window.open("", "_blank", "width=350,height=700")
			printWindow.document.write(html)
			printWindow.document.close()
			printWindow.onload = () => {
				setTimeout(() => printWindow.print(), 250)
			}
			
			return { success: true, method: "browser" }
		}
	} catch (error) {
		log.error("Failed to print Z Report:", error)
		throw error
	}
}

/**
 * Get X Report data for preview (without printing)
 */
export async function getXReportData(posProfile, openingShift = null) {
	return await call("pos_next.api.shift_reports.get_x_report_data", {
		pos_profile: posProfile,
		opening_shift: openingShift,
	})
}

/**
 * Get Z Report data for preview (without printing)
 */
export async function getZReportData(posProfile, openingShift = null) {
	return await call("pos_next.api.shift_reports.get_z_report_data", {
		pos_profile: posProfile,
		opening_shift: openingShift,
	})
}
