"""
Генератор актов КС-2.
Использует твой оригинальный код с ks2.py + добавляет поддержку XLSX.
"""
import os
import asposecells
asposecells.startJVM()
from asposecells.api import Workbook, SaveFormat, PdfSaveOptions
import gc
import traceback
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def fill_ks2(template_path, output_path, data, format='pdf'):
    """
    Заполнение шаблона КС-2 и экспорт в PDF или XLSX.
    
    Args:
        template_path: путь к ks2.xlsx
        output_path: путь для сохранения результата
        data: dict с данными для заполнения
        format: 'pdf' или 'xlsx'
    
    Returns:
        str: путь к сгенерированному файлу
    """
    wb = None
    try:
        # 1. Инициализация Aspose.Cells с настройкой шрифтов
        font_dir = "/usr/share/fonts"
        # Устанавливаем пути к шрифтам через системное свойство Java
        import jpype
        jpype.JClass('java.lang.System').setProperty('aspose.fonts.dir', font_dir)
        logger.info(f" Настроена папка со шрифтами: {font_dir}")
        
        wb = Workbook(template_path)
        ws = wb.getWorksheets().get(0)

        vat_rate = float(str(data.get("vat_rate", "20%")).replace('%', '')) / 100
        
        # 2. Заполнение шапки (твой оригинальный код)
        ws.getCells().get("E7").putValue(data.get("investor", "   "))
        ws.getCells().get("G9").putValue(data.get("customer", "   "))
        ws.getCells().get("H11").putValue(data.get("contractor", "   "))
        ws.getCells().get("E13").putValue(data.get("construction", "   "))
        ws.getCells().get("C15").putValue(data.get("object", "   "))
        ws.getCells().get("N24").putValue(data.get("document_number", "   "))
        ws.getCells().get("Q24").putValue(data.get("contract_date", "   "))
        ws.getCells().get("W24").putValue(data.get("report_from", "   "))
        ws.getCells().get("AA24").putValue(data.get("report_to", "   "))
        ws.getCells().get("AD6").putValue(data.get("okpo_investor", "   "))
        ws.getCells().get("AD8").putValue(data.get("okpo_customer", "   "))
        ws.getCells().get("AD10").putValue(data.get("okpo_contractor", "   "))
        ws.getCells().get("AD16").putValue(data.get("okdp", "   "))
        ws.getCells().get("AD18").putValue(data.get("contract_number", "   "))
        ws.getCells().get("AD19").putValue(data.get("day_contract", "   "))
        ws.getCells().get("AF19").putValue(data.get("month_contract", "   "))
        ws.getCells().get("AG19").putValue(data.get("year_contract", "   "))
        ws.getCells().get("O27").putValue(data.get("smeta", "   "))
        ws.getCells().get("S56").putValue(f"Сумма НДС {int(round(vat_rate * 100))}%")
        
        # 3. Заполнение подписей
        ws.getCells().get("F59").putValue(data.get("surrender_position", "   "))
        ws.getCells().get("N60").putValue(data.get("surrender_signature", "   "))
        ws.getCells().get("F64").putValue(data.get("accept_position", "   "))
        ws.getCells().get("N65").putValue(data.get("accept_signature", "   "))
        
        # 4. Разделение и заполнение работ
        start_row_1 = 32
        end_row_1_data = 37
        capacity_p1 = end_row_1_data - start_row_1 + 1  # 6 строк
        
        works = data.get("works", [])
        works_p1 = works[:capacity_p1]
        works_p2 = works[capacity_p1:]
        
        # Очищаем области данных
        for r in range(start_row_1, end_row_1_data + 1):
            for c in range(32):
                ws.getCells().get(r - 1, c).putValue("  ")
        for r in range(45, 54):
            for c in range(32):
                ws.getCells().get(r - 1, c).putValue("  ")
        
        # Заполняем 1-ю страницу
        row = start_row_1
        for i, work in enumerate(works_p1, start=1):
            ws.getCells().get(row - 1, 0).putValue(i)
            ws.getCells().get(row - 1, 2).putValue(work.get("position", "   "))
            ws.getCells().get(row - 1, 5).putValue(work.get("name", "   "))
            ws.getCells().get(row - 1, 14).putValue(work.get("number_pricelist", "   "))
            ws.getCells().get(row - 1, 16).putValue(work.get("unit_of_measurement", "   "))
            ws.getCells().get(row - 1, 20).putValue(work.get("quantity", 0))
            ws.getCells().get(row - 1, 24).putValue(work.get("price", 0))
            ws.getCells().get(row - 1, 29).putValue(work.get("quantity", 0) * work.get("price", 0))
            row += 1
        
        # Логика обработки страниц
        if not works_p2:
            # Сценарий 1: Все работы на 1-й странице
            logger.info(" Сценарий 1: Все работы на 1-й странице")
            
            ws.getCells().insertRows(39, 4)
            ws.getCells().copyRows(ws.getCells(), 57, 39, 4)
            ws.getCells().deleteRows(45, 16)
            
            # Удаляем пустые строки
            for r in range(39, start_row_1 - 1, -1):
                cell_val = ws.getCells().get(r - 1, 5).getValue()
                if cell_val is None or str(cell_val).strip() in ("", " "):
                    ws.getCells().deleteRows(r - 1, 1)
            
            # Подсчёт итогов
            vat_rate = float(str(data.get("vat_rate", "20")).replace('%', '')) / 100
            total_p1 = sum(w.get("quantity", 0) * w.get("price", 0) for w in works_p1)
            vat_p1 = total_p1 * vat_rate
            total_with_vat_p1 = total_p1 + vat_p1
            
            summary_start_p1 = start_row_1 + len(works_p1)
            ws.getCells().get(summary_start_p1 - 1, 29).putValue(round(total_p1, 2))
            ws.getCells().get(summary_start_p1, 29).putValue(round(total_p1, 2))
            ws.getCells().get(summary_start_p1 + 1, 29).putValue(round(vat_p1, 2))
            ws.getCells().get(summary_start_p1 + 2, 29).putValue(round(total_with_vat_p1, 2))
            
        else:
            # Сценарий 2: Работы на двух страницах
            logger.info(" Сценарий 2: Работы переносятся на 2-ю страницу")
            
            start_row_2 = 45
            row_2 = start_row_2
            start_num_2 = capacity_p1 + 1
            
            for i, work in enumerate(works_p2, start=start_num_2):
                ws.getCells().get(row_2 - 1, 0).putValue(i)
                ws.getCells().get(row_2 - 1, 2).putValue(work.get("position", "   "))
                ws.getCells().get(row_2 - 1, 5).putValue(work.get("name", "   "))
                ws.getCells().get(row_2 - 1, 14).putValue(work.get("number_pricelist", "   "))
                ws.getCells().get(row_2 - 1, 16).putValue(work.get("unit_of_measurement", "   "))
                ws.getCells().get(row_2 - 1, 20).putValue(work.get("quantity", 0))
                ws.getCells().get(row_2 - 1, 24).putValue(work.get("price", 0))
                ws.getCells().get(row_2 - 1, 29).putValue(work.get("quantity", 0) * work.get("price", 0))
                row_2 += 1
            
            # Удаляем пустые строки
            for r in range(53, start_row_2 - 1, -1):
                cell_val = ws.getCells().get(r - 1, 5).getValue()
                if cell_val is None or str(cell_val).strip() in ("", " "):
                    ws.getCells().deleteRows(r - 1, 1)
            for r in range(38, start_row_1 - 1, -1):
                cell_val = ws.getCells().get(r - 1, 5).getValue()
                if cell_val is None or str(cell_val).strip() in ("", " "):
                    ws.getCells().deleteRows(r - 1, 1)
            
            # Подсчёт итогов
            vat_rate = float(str(data.get("vat_rate", "20")).replace('%', '')) / 100
            total_p1 = sum(w.get("quantity", 0) * w.get("price", 0) for w in works_p1)
            total_p2 = sum(w.get("quantity", 0) * w.get("price", 0) for w in works_p2)

            
            ws.getCells().get(37, 29).putValue(round(total_p1, 2))
            
            grand_total = total_p1 + total_p2
            grand_vat = grand_total * vat_rate
            grand_total_vat = grand_total + grand_vat
            
            summary_start_p2 = start_row_2 + len(works_p2)
            ws.getCells().get(summary_start_p2 - 2, 29).putValue(round(total_p2, 2))
            ws.getCells().get(summary_start_p2 - 1, 29).putValue(round(grand_total, 2))
            ws.getCells().get(summary_start_p2, 29).putValue(round(grand_vat, 2))
            ws.getCells().get(summary_start_p2 + 1, 29).putValue(round(grand_total_vat, 2))
        
        # 5. Экспорт
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        if format == 'xlsx':
            wb.save(output_path, SaveFormat.XLSX)
            logger.info(f" XLSX сохранён: {output_path}")
        else:
            # Настройки PDF для корректного отображения на Linux
            pdf_options = PdfSaveOptions()
            pdf_options.setOnePagePerSheet(False)
            pdf_options.setAllColumnsInOnePagePerSheet(True)
            
            wb.save(output_path, pdf_options)
            logger.info(f" PDF сохранён: {output_path}")
        
        logger.info(f" Заполнено работ: {len(works)}")
        return output_path
        
    except Exception as e:
        logger.error(f" Ошибка генерации КС-2: {e}")
        traceback.print_exc()
        raise
    finally:
        if wb:
            del wb
        gc.collect()

