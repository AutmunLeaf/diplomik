"""
Генератор справок КС-3.
Использует твой оригинальный код с ks3.py + добавляет поддержку XLSX.
"""
import os
import gc
import traceback
import logging
from django.conf import settings

# Явная настройка JAVA_HOME перед любым импортом asposecells
import os as _os
if not _os.environ.get('JAVA_HOME'):
    _os.environ['JAVA_HOME'] = '/usr/lib/jvm/java-21-openjdk-amd64'

# Инициализация JVM только один раз ПЕРЕД любыми другими импортами asposecells
_jvm_initialized = False
try:
    import jpype
    if not jpype.isJVMStarted():
        import asposecells
        # Явно указываем путь к libjvm.so через параметры запуска
        jvm_path = jpype.getDefaultJVMPath()
        asposecells.startJVM(jvm_path)
        _jvm_initialized = True
        # Настраиваем пути к шрифтам
        jpype.JClass('java.lang.System').setProperty('aspose.fonts.dir', '/usr/share/fonts')
except Exception as e:
    logging.warning(f"Предупреждение при инициализации JVM: {e}")

# Теперь импортируем API только после успешного запуска JVM
from asposecells.api import Workbook, SaveFormat, PdfSaveOptions

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
        # JVM и шрифты уже настроены при импорте модуля
        logger.info(" Используем настроенные пути к шрифтам: /usr/share/fonts")
        
        wb = Workbook(template_path)
        ws = wb.getWorksheets().get(0)
        
        # 2. Заполнение шапки
        ws.getCells().get("F7").putValue(data.get("investor", "     "))
        ws.getCells().get("M9").putValue(data.get("customer", "     "))
        ws.getCells().get("N11").putValue(data.get("contractor", "     "))
        ws.getCells().get("E13").putValue(data.get("construction", "     "))
        ws.getCells().get("X22").putValue(data.get("document_number", "     "))
        ws.getCells().get("AG22").putValue(data.get("contract_date", "     "))
        ws.getCells().get("AR22").putValue(data.get("report_from", "     "))
        ws.getCells().get("AW22").putValue(data.get("report_to", "     "))
        ws.getCells().get("AP6").putValue(data.get("okpo_investor", "     "))
        ws.getCells().get("AP8").putValue(data.get("okpo_customer", "     "))
        ws.getCells().get("AP10").putValue(data.get("okpo_contractor", "     "))
        ws.getCells().get("AP14").putValue(data.get("okdp", "     "))
        ws.getCells().get("AP16").putValue(data.get("contract_number", "     "))
        ws.getCells().get("AP17").putValue(data.get("day_contract", "     "))
        ws.getCells().get("AT17").putValue(data.get("month_contract", "     "))
        ws.getCells().get("AX17").putValue(data.get("year_contract", "     "))
        ws.getCells().get("AP18").putValue(data.get("operation", "     "))
        
        # 3. Подписи
        ws.getCells().get("N48").putValue(data.get("surrender_position", "     "))
        ws.getCells().get("AJ49").putValue(data.get("surrender_signature", "     "))
        ws.getCells().get("N53").putValue(data.get("accept_position", "     "))
        ws.getCells().get("AJ54").putValue(data.get("accept_signature", "     "))
        
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
                ws.getCells().get(r - 1, c).putValue("    ")
        
        # Заполнение
        row = start_row
        total_report_period = 0
        
        for i, work in enumerate(works, start=1):
            ws.getCells().get(row - 1, 0).putValue(i)
            ws.getCells().get(row - 1, 3).putValue(work.get("name", "     "))
            ws.getCells().get(row - 1, 26).putValue(work.get("code", "     "))
            ws.getCells().get(row - 1, 30).putValue(work.get("cost_from_start", 0))
            ws.getCells().get(row - 1, 37).putValue(work.get("cost_from_year", 0))
            
            cost_period = work.get("cost_report_period", 0)
            ws.getCells().get(row - 1, 45).putValue(cost_period)
            total_report_period += cost_period
            row += 1
        
        # Итого
        ws.getCells().get(44, 45).putValue(total_report_period)
        
        # НДС и итог с НДС
        vat_rate = float(str(data.get("vat_rate", "20%")).replace('%', '')) / 100
        vat_amount = total_report_period * vat_rate
        total_with_vat = total_report_period + vat_amount
        
        ws.getCells().get(45, 44).putValue(f"Сумма НДС {int(round(vat_rate * 100))}%")
        ws.getCells().get(45, 45).putValue(round(vat_amount, 2))
        ws.getCells().get(46, 45).putValue(round(total_with_vat, 2))
        
        # Удаляем пустые строки
        for r in range(44, start_row - 1, -1):
            cell_val = ws.getCells().get(r - 1, 3).getValue()
            if cell_val is None or str(cell_val).strip() in ("", " ", "", " "):
                ws.getCells().deleteRows(r - 1, 1)
        
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