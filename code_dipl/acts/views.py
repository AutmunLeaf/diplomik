"""
Представления (views) для приложения актов.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, HttpResponse, JsonResponse
from django.urls import reverse
from django.conf import settings
from django.db import transaction
import os
import tempfile
import json

from .models import ActInput, WorkItem, OrgConstants
from .forms import (
    ActInputForm, KS2WorkFormSet, KS3WorkFormSet,
    KS2WorkForm, KS3WorkForm
)
from .utils.ks2_gen import fill_ks2
from .utils.ks3_gen import fill_ks3

import time
import logging

logger = logging.getLogger(__name__)


@login_required
def index(request):
    """Главная страница — список актов"""
    acts = ActInput.objects.select_related('created_by').all()[:50]
    
    # Группировка по типам
    ks2_acts = [a for a in acts if a.act_type == 'ks2']
    ks3_acts = [a for a in acts if a.act_type == 'ks3']
    
    return render(request, 'acts/index.html', {
        'ks2_acts': ks2_acts,
        'ks3_acts': ks3_acts,
    })


@login_required
def create_act(request, act_type):
    """Создание нового акта (КС-2 или КС-3)"""
    if act_type not in ['ks2', 'ks3']:
        messages.error(request, 'Неверный тип акта')
        return redirect('acts:index')
    
    # Выбираем FormSet в зависимости от типа
    FormSetFactory = KS2WorkFormSet if act_type == 'ks2' else KS3WorkFormSet
    
    if request.method == 'POST':
        form = ActInputForm(request.POST)
        formset = FormSetFactory(request.POST, prefix='works') # <-- ЭКЗЕМПЛЯР с данными

        # 🔍 ОТЛАДКА: выводим ошибки в консоль
        if not form.is_valid():
            print("❌ Ошибки формы:", form.errors)
        if not formset.is_valid():
            print("❌ Ошибки формсета:", formset.errors)
        
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                # Сохраняем акт
                act = form.save(commit=False)
                act.act_type = act_type
                act.created_by = request.user
                act.save()
                
                # Сохраняем работы
                works = formset.save(commit=False)
                for work in works:
                    work.act = act
                    work.save()
                
                # Удаляем помеченные на удаление
                for obj in formset.deleted_objects:
                    obj.delete()

                messages.success(
                    request, 
                    f'✅ {act.get_act_type_display()} №{act.document_number} создан! '
                    'Теперь можно скачать документ.'
                )
                return redirect('acts:download', pk=act.pk, format='pdf')
    else:
        # GET — пустая форма с предзаполнением статики
        form = ActInputForm(initial={
            'act_type': act_type,
            'contractor': OrgConstants.NAME,
            'contractor_okpo': OrgConstants.OKPO,
            'okdp': OrgConstants.OKDP,
        })
        formset = FormSetFactory(prefix='works')  # <-- ЭКЗЕМПЛЯР, а не класс!
    
    return render(request, 'acts/act_form.html', {
        'form': form,
        'formset': formset,
        'act_type': act_type,
        'act_type_display': 'КС-2' if act_type == 'ks2' else 'КС-3',
    })


@login_required
def edit_act(request, pk):
    """Редактирование существующего акта"""
    act = get_object_or_404(ActInput, pk=pk)
    
    # Выбираем правильный FormSet
    if act.act_type == 'ks2':
        FormSet = KS2WorkFormSet
    else:
        FormSet = KS3WorkFormSet
    
    if request.method == 'POST':
        form = ActInputForm(request.POST, instance=act)
        
        # ✅ КЛЮЧЕВОЕ: instance=act + prefix='works'
        formset = FormSet(request.POST, instance=act, prefix='works')
        
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                # 1. Сохраняем шапку акта
                act = form.save()
                print(f"✅ Saved act header: {act.document_number}")
                
                # 2. Сохраняем работы — это обновит существующие И создаст новые
                instances = formset.save(commit=False)
                for instance in instances:
                    instance.act = act  # ✅ Явно привязываем к акту
                    instance.save()
                    print(f"✅ Saved work: {instance.name[:30]}...")
                
                # 3. Удаляем помеченные на удаление
                for obj in formset.deleted_objects:
                    obj.delete()
                    print(f"🗑️ Deleted work: {obj.name[:30]}...")
            
            messages.success(request, f'✅ Акт №{act.document_number} обновлён!')
            return redirect('acts:detail', pk=act.pk)
        else:
            # Выводим ошибки для отладки
            if not form.is_valid():
                print(f"❌ Form errors: {form.errors}")
            if not formset.is_valid():
                print(f"❌ Formset errors: {formset.errors}")
    else:
        # GET — загружаем существующие данные
        form = ActInputForm(instance=act)
        formset = FormSet(instance=act, prefix='works')  # ✅ prefix обязателен
    
    return render(request, 'acts/act_form.html', {
        'form': form,
        'formset': formset,
        'act_type': act.act_type,
        'act_type_display': act.get_act_type_display(),
        'act': act,
    })


@login_required
def detail_act(request, pk):
    """Просмотр акта с кнопками скачивания"""
    act = get_object_or_404(ActInput.objects.prefetch_related('works'), pk=pk)
    return render(request, 'acts/act_detail.html', {'act': act})


@login_required
def download_act(request, pk, format='pdf'):
    if format not in ['pdf', 'xlsx']:
        return HttpResponse('Неверный формат', status=400)

    # 1. Получаем акт БЕЗ prefetch_related, чтобы избежать кэша
    act = get_object_or_404(ActInput, pk=pk)
    act.refresh_from_db()

    # 2. Явно запрашиваем работы свежим SQL-запросом
    works_qs = WorkItem.objects.filter(act=act).order_by('order', 'id')

    # 🔍 ОТЛАДКА: выводим в консоль то, что реально пойдёт в генератор
    logger.info(f"📥 Генерация {format} для акта {act.document_number}")
    for i, w in enumerate(works_qs):
        if act.act_type == 'ks2':
            logger.info(f"   Работа {i+1}: {w.name} | Кол-во: {w.quantity} | Цена: {w.price}")
        else:
            logger.info(f"   Работа {i+1}: {w.name} | За период: {w.cost_report_period}")

    template_path = os.path.join(settings.MEDIA_ROOT, 'templates', act.get_template_name())
    if not os.path.exists(template_path):
        messages.error(request, f'❌ Шаблон {act.get_template_name()} не найден!')
        return redirect('acts:detail', pk=act.pk)

    # 3. Собираем словарь данных из свежих объектов
    data = {
        "investor": act.investor, "okpo_investor": act.investor_okpo,
        "customer": act.customer, "okpo_customer": act.customer_okpo,
        "contractor": act.contractor, "okpo_contractor": act.contractor_okpo,
        "construction": act.construction, "object": act.object_name,
        "operation": act.operation, "okdp": act.okdp,
        "document_number": act.document_number,
        "contract_number": act.contract_number,
        "contract_date": act.contract_date.strftime('%d.%m.%Y'),
        "day_contract": act.contract_date.day,
        "month_contract": act.contract_date.month,
        "year_contract": act.contract_date.year,
        "report_from": act.report_from.strftime('%d.%m.%Y'),
        "report_to": act.report_to.strftime('%d.%m.%Y'),
        "surrender_position": act.surrender_position,
        "surrender_signature": act.surrender_signature,
        "accept_position": act.accept_position,
        "accept_signature": act.accept_signature,
        "vat_rate": act.vat_rate,
        "smeta": act.smeta,
        "works": [
            {
                "position": w.position, "name": w.name, "code": w.code,
                "number_pricelist": w.number_pricelist,
                "unit_of_measurement": w.unit,
                "quantity": float(w.quantity or 0),
                "price": float(w.price or 0),
                "cost_from_start": float(w.cost_from_start),
                "cost_from_year": float(w.cost_from_year),
                "cost_report_period": float(w.cost_report_period),
            }
            for w in works_qs  # ✅ Используем свежий QuerySet, а не act.works.all()
        ]
    }

    output_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{format}", dir=settings.MEDIA_ROOT / 'output') as tmp:
            output_path = tmp.name

        if act.act_type == 'ks2':
            from .utils.ks2_gen import fill_ks2
            fill_ks2(template_path, output_path, data, format=format)
        else:
            from .utils.ks3_gen import fill_ks3
            fill_ks3(template_path, output_path, data, format=format)

        with open(output_path, 'rb') as f:
            file_content = f.read()

        timestamp = int(time.time())
        filename = f"{act.act_type.upper()}_{act.document_number}_{timestamp}.{format}"
        content_type = 'application/pdf' if format == 'pdf' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

        response = HttpResponse(file_content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response

    except Exception as e:
        logger.error(f"❌ Ошибка генерации: {e}")
        messages.error(request, f'❌ Ошибка генерации: {e}')
        return redirect('acts:detail', pk=act.pk)
        
    finally:
        if output_path and os.path.exists(output_path):
            try:
                os.unlink(output_path)
            except PermissionError:
                pass


@login_required
def delete_act(request, pk):
    """Удаление акта (только черновики)"""
    act = get_object_or_404(ActInput, pk=pk)
    
    if act.status != 'draft':
        messages.error(request, '❌ Можно удалять только черновики')
        return redirect('acts:detail', pk=act.pk)
    
    if request.method == 'POST':
        doc_num = act.document_number
        act.delete()
        messages.success(request, f'🗑️ Акт №{doc_num} удалён')
        return redirect('acts:index')
    
    return render(request, 'acts/act_confirm_delete.html', {'act': act})


# API для динамического добавления работ (AJAX)
@login_required
def api_add_work(request, act_type):
    """Возвращает пустую форму работы для JS-добавления"""
    if act_type == 'ks2':
        form = KS2WorkForm(prefix='works-__prefix__')
    elif act_type == 'ks3':
        form = KS3WorkForm(prefix='works-__prefix__')
    else:
        return JsonResponse({'error': 'Неверный тип'}, status=400)
    
    return JsonResponse({'html': form.as_p()})