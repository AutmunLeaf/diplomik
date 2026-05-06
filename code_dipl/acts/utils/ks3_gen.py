"""
Генератор справок КС-3.
Использует твой оригинальный код с ks3.py + добавляет поддержку XLSX.
"""
import os
import aspose.cells as ac
from aspose.cells import SaveFormat
import gc
import traceback
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def fill_ks3(template_path, output_path, data, format='pdf'):
    """
    Заполнение шаблона КС-3 и экспорт в PDF или XLSX.
    
    Args:
        template_path: путь к ks3.xlsx
        output_path: путь для сохранения результата
        data: dict с данными для заполнения
        format: 'pdf' или 'xlsx'
    
    Returns:
        str: путь к сгенерированному файлу
    """
    wb = None
    try:
        # 1. Инициализация
        wb = ac.Workbook(template_path)
        ws = wb.worksheets[0]
        
        # 2. Заполнение шапки
        ws.cells.get("F7").put_value(data.get("investor", "     "))
        ws.cells.get("M9").put_value(data.get("customer", "     "))
        ws.cells.get("N11").put_value(data.get("contractor", "     "))
        ws.cells.get("E13").put_value(data.get("construction", "     "))
        ws.cells.get("X22").put_value(data.get("document_number", "     "))
        ws.cells.get("AG22").put_value(data.get("contract_date", "     "))
        ws.cells.get("AR22").put_value(data.get("report_from", "     "))
        ws.cells.get("AW22").put_value(data.get("report_to", "     "))
        ws.cells.get("AP6").put_value(data.get("okpo_investor", "     "))
        ws.cells.get("AP8").put_value(data.get("okpo_customer", "     "))
        ws.cells.get("AP10").put_value(data.get("okpo_contractor", "     "))
        ws.cells.get("AP14").put_value(data.get("okdp", "     "))
        ws.cells.get("AP16").put_value(data.get("contract_number", "     "))
        ws.cells.get("AP17").put_value(data.get("day_contract", "     "))
        ws.cells.get("AT17").put_value(data.get("month_contract", "     "))
        ws.cells.get("AX17").put_value(data.get("year_contract", "     "))
        ws.cells.get("AP18").put_value(data.get("operation", "     "))
        
        # 3. Подписи
        ws.cells.get("N48").put_value(data.get("surrender_position", "     "))
        ws.cells.get("AJ49").put_value(data.get("surrender_signature", "     "))
        ws.cells.get("N53").put_value(data.get("accept_position", "     "))
        ws.cells.get("AJ54").put_value(data.get("accept_signature", "     "))
        
        # 4. Заполнение работ (макс 14)
        start_row = 31
        end_row = 44
        
        works = data.get("works", [])
        if len(works) > 14:
            logger.warning(f" Работ больше 14 ({len(works)}), будут заполнены только первые 14")
            works = works[:14]
        
        # Очистка
        for r in range(start_row, end_row + 1):
            for c in range(50):
                ws.cells.get(r - 1, c).put_value("    ")
        
        # Заполнение
        row = start_row
        total_report_period = 0
        
        for i, work in enumerate(works, start=1):
            ws.cells.get(row - 1, 0).put_value(i)
            ws.cells.get(row - 1, 3).put_value(work.get("name", "     "))
            ws.cells.get(row - 1, 26).put_value(work.get("code", "     "))
            ws.cells.get(row - 1, 30).put_value(work.get("cost_from_start", 0))
            ws.cells.get(row - 1, 37).put_value(work.get("cost_from_year", 0))
            
            cost_period = work.get("cost_report_period", 0)
            ws.cells.get(row - 1, 45).put_value(cost_period)
            total_report_period += cost_period
            row += 1
        
        # Итого
        ws.cells.get(44, 45).put_value(total_report_period)
        
        # НДС и итог с НДС
        vat_rate = float(str(data.get("vat_rate", "20%")).replace('%', '')) / 100
        vat_amount = total_report_period * vat_rate
        total_with_vat = total_report_period + vat_amount
        
        ws.cells.get(45, 44).put_value(f"Сумма НДС {int(round(vat_rate * 100))}%")
        ws.cells.get(45, 45).put_value(round(vat_amount, 2))
        ws.cells.get(46, 45).put_value(round(total_with_vat, 2))
        
        # Удаляем пустые строки
        for r in range(44, start_row - 1, -1):
            cell_val = ws.cells.get(r - 1, 3).value
            if cell_val is None or str(cell_val).strip() in ("", " ", "", " "):
                ws.cells.delete_rows(r - 1, 1)
        
        # 5. Экспорт
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        if format == 'xlsx':
            wb.save(output_path, SaveFormat.XLSX)
            logger.info(f" XLSX сохранён: {output_path}")
        else:
            wb.save(output_path, SaveFormat.PDF)
            logger.info(f" PDF сохранён: {output_path}")
        
        logger.info(f" Заполнено работ: {len(works)} из 14")
        logger.info(f" Итого за период: {total_report_period}")
        
        return output_path
        
    except Exception as e:
        logger.error(f" Ошибка генерации КС-3: {e}")
        traceback.print_exc()
        raise
    finally:
        if wb:
            del wb
        gc.collect()