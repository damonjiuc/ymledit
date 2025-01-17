from config import ftp, ftp_cp1, ftp_spbl, ftp_lenp, ftp_pd, ftp_rd, url, url_cp1, url_spbl, url_lenp, url_pd, url_rd
import xmltodict
import requests


input_file = 'input.xml'
output_file = 'edited.xml'

collection_eq_sp = {
    '1056': 'laminat',
    '1057': 'parket',
    '1058': 'inzhenernaya-doska',
    '1059': 'pvkh-pokrytiya',
    '1062': 'massivnaya-doska',
    '1063': 'modulnyy-parket',
    '1065': 'terrasnaya-doska',
    '1092': 'probkovye-pokrytiya',
    '1074': 'accessories',
    '1083': 'accessories',
    '1099': 'accessories',
    '1095': 'plintusy',
    '1096': 'plintusy'
}


def get_dict(path):
    with open(path, 'r', encoding='UTF-8') as file:
        yml = file.read()
        my_dict = xmltodict.parse(yml)
    return my_dict


def get_xml(current_url):
    response = requests.get(current_url)

    with open(input_file, "wb") as file:
        file.write(response.content)


def write_xml(file_to_write, selected_ftp):
    with open(file_to_write, "rb") as file:
        selected_ftp.storbinary("STOR main.xml", file)


def get_categories(dict_w_data):
    categories = {}
    for category in dict_w_data['yml_catalog']['shop']['categories']['category']:
        categories[category['@id']] = category['#text']
    return categories

def clear_categories(dict_w_data):
    top_lvl_cat = []
    from_child = {}
    from_parent = {}

    for cat in dict_w_data['yml_catalog']['shop']['categories']['category']:
        if '@parentId' in cat:
            from_child[cat['@id']] = cat['@parentId']
            cur_parent_cat = from_parent.get(cat['@parentId'], list())
            cur_parent_cat.append(cat['@id'])
            from_parent[cat['@parentId']] = cur_parent_cat
        else:
            top_lvl_cat.append(cat)

    dict_w_data['yml_catalog']['shop']['categories']['category'] = top_lvl_cat

    return dict_w_data, from_child, from_parent, top_lvl_cat

def clear_doors_categories(dict_w_data):
    new_cat = []

    for cat in dict_w_data['yml_catalog']['shop']['categories']['category']:
        if cat['@id'] in ['1', '2', '314']:
            new_cat.append(cat)

    dict_w_data['yml_catalog']['shop']['categories']['category'] = new_cat

def set_collections(dict_w_data, collection_eq):
    for offer in dict_w_data['yml_catalog']['shop']['offers']['offer']:
        offer['collectionId'] = collection_eq[offer['categoryId']]

def clear_currencies(dict_w_data):
    rur_only_currencies = []
    for currency in dict_w_data['yml_catalog']['shop']['currencies']['currency']:
        if currency['@id'] == 'RUB':
            rur_only_currencies.append(currency)

    dict_w_data['yml_catalog']['shop']['currencies']['currency'] = rur_only_currencies

def filter_doors_rd(dict_w_data, used_categories, erased_categories, equal_categories):
    filtered_categories = []
    for offer in dict_w_data['yml_catalog']['shop']['offers']['offer']:
        if offer['categoryId'] == '1' or offer['categoryId'] == '2':
            filtered_categories.append(offer)
        if offer['categoryId'] in erased_categories:
            continue
        elif offer['categoryId'] in used_categories and offer['categoryId'] not in ['1', '2']:
            offer['categoryId'] = equal_categories[offer['categoryId']]
            filtered_categories.append(offer)

    print(f'\nВсего было дверей: {len(filtered_categories)}')

    dict_w_data['yml_catalog']['shop']['offers']['offer'] = filtered_categories

def filter_doors_colors(dict_w_data):
    doors_tree = {}
    doors_wo_vars = []
    doors_w_vars = []
    outside_doors = []

    for offer in dict_w_data['yml_catalog']['shop']['offers']['offer']:
        if offer['categoryId'] == '1':
            outside_doors.append(offer)

        if '@group_id' in offer.keys():
            group_id = offer['@group_id']

            if not group_id in doors_tree.keys():
                doors_tree[group_id] = [[False, False, False], [], []]

            cur_params = [False, False, False]

            for param in offer['param']:
                if param['@name'] == 'Размер':
                    doors_tree[group_id][0][0] = True
                    cur_params[0] = param['#text']
                if param['@name'] == 'Системы открывания':
                    doors_tree[group_id][0][1] = True
                    cur_params[1] = param['#text']
                if param['@name'] == 'Остекление':
                    doors_tree[group_id][0][2] = True
                    cur_params[2] = param['#text']

            if cur_params not in doors_tree[group_id][1]:
                doors_tree[group_id][1].append(cur_params)
                doors_w_vars.append(offer)

        else:
            doors_wo_vars.append(offer)

    print(f'Дверей осталось после фильтрации: {len(doors_w_vars)}')
    dict_w_data['yml_catalog']['shop']['offers']['offer'] = doors_w_vars


def filter_sale(dict_w_data):
    doors = []
    for offer in dict_w_data['yml_catalog']['shop']['offers']['offer']:
        for param in offer['param']:
            if param['@name'] == 'Распродажа 2025':
                doors.append(offer)
    print(f'Дверей осталось после фильтрации: {len(doors)}')
    dict_w_data['yml_catalog']['shop']['offers']['offer'] = doors


def edit_offers(dict_w_data, categories):
    for offer in dict_w_data['yml_catalog']['shop']['offers']['offer']:
        description = []

        typeprefix = categories[offer['categoryId']]
        offer['typePrefix'] = typeprefix
        description.append(typeprefix + '.')

        vendor = offer['vendor']
        model = offer['model']
        if vendor in model:
            model = model.replace(vendor, '').strip()
            offer['model'] = model

        for param in offer['param']:
            if param['@name'] == 'Площадь в упаковке, м2':
                s = float(param['#text'].replace(',', '.'))
                price = int(round(int(offer['price']) / s))
                offer['price'] = price

            if param['@name'] == 'Класс':
                cla = param['#text'] + '.'
                description.append(cla)

            if param['@name'] == 'Тип соединения':
                s_type = param['#text'] + '.'
                description.append('Тип соединения:')
                description.append(s_type)

            if param['@name'] == 'Размер':
                size = param['#text'] + '.'
                description.append('Размер:')
                description.append(size)

            if param['@name'] == 'Тип рисунка':
                art = param['#text'] + '.'
                description.append('Рисунок:')
                description.append(art)

            if param['@name'] == 'Селекция':
                sel = param['#text'] + '.'
                description.append('Селекция:')
                description.append(sel)

        description = ' '.join(description)
        offer['description'] = description

def edit_offers_pl(dict_w_data, categories):
    for offer in dict_w_data['yml_catalog']['shop']['offers']['offer']:
        description = []

        typeprefix = categories[offer['categoryId']]
        offer['typePrefix'] = typeprefix
        description.append(typeprefix + '.')

        if 'vendor' in offer:
            vendor = offer['vendor']
            model = offer['model']
            if vendor in model:
                model = model.replace(vendor, '').strip()
                offer['model'] = model
        else:
            print(offer['model'])
            continue

        for param in offer['param']:
            if param['@name'] == 'Назначение':
                used_for = param['#text'] + '.'
                description.append('Назначение:')
                description.append(used_for)

            if param['@name'] == 'Материал':
                mats = param['#text'] + '.'
                description.append('Материал:')
                description.append(mats)

            if param['@name'] == 'Цвет':
                color = param['#text'] + '.'
                description.append('Цвет:')
                description.append(color)

            if param['@name'] == 'Длина':
                length = param['#text'] + '.'
                description.append('Длина:')
                description.append(length)

            if param['@name'] == 'Ширина':
                width = param['#text'] + '.'
                description.append('Ширина:')
                description.append(width)

        description = ' '.join(description)
        offer['description'] = description

def edit_offers_doors(dict_w_data, categories):
    for offer in dict_w_data['yml_catalog']['shop']['offers']['offer']:
        description = []

        typeprefix = categories[offer['categoryId']]
        offer['typePrefix'] = typeprefix
        description.append(typeprefix + '.')

        if offer['categoryId'] == '1':
            offer['collectionId'] = 'vhodnie'
        elif offer['categoryId'] == '2':
            offer['collectionId'] = 'komnatnie'

        # if 'vendor' in offer:
        #     vendor = offer['vendor']
        #     model = offer['model']
        #     if vendor in model:
        #         model = model.replace(vendor, '').strip()
        #         offer['model'] = model
        # else:
        #     print(f'Нет вендора у {offer['model']}')
        #     continue

        for param in offer['param']:
            if param['@name'] == 'Модель':
                offer['model'] = param['#text']

            if param['@name'] == 'Размер':
                size = param['#text'] + '.'
                description.append('Размер:')
                description.append(size)

            if param['@name'] == 'Покрытие':
                cover = param['#text'] + '.'
                description.append('Покрытие:')
                description.append(cover)

            if param['@name'] == 'Вид':
                type = param['#text'] + '.'
                description.append('Вид:')
                description.append(type)

            if param['@name'] == 'Системы открывания':
                openin = param['#text']

                if openin == 'Invisible':
                    openin = 'Скрытого монтажа'
                if openin == 'РОТО':
                    openin = 'Поворотная'
                if openin == 'Купе':
                    openin = 'Раздвижная'

                param['#text'] = openin

                openin = param['#text'] + '.'
                description.append('Тип открывания:')
                description.append(openin)

            if param['@name'] == 'Уплотнитель':
                sealer = param['#text'] + '.'
                description.append('Уплотнитель:')
                description.append(sealer)

            if param['@name'] == 'Толщина':
                fat = param['#text'] + '.'
                description.append('Толщина:')
                description.append(fat)

            if param['@name'] == 'Сталь':
                steel = param['#text'] + '.'
                description.append('Сталь:')
                description.append(steel)

            if param['@name'] == 'Замки':
                locks = param['#text'] + '.'
                description.append('Замки:')
                description.append(locks)

        description = ' '.join(description)
        offer['description'] = description

    return dict_w_data

def set_pd_collections(dict_w_data):
    collections_pd = {'collection':
                       [{'@id': 'komnatnie', 'url': 'https://profildoors.sale/catalog/mezhkomnatnye-dveri/',
                         'picture': 'https://profildoors.sale/media/297/297340.png',
                         'name': 'Межкомнатные двери в магазинах "Profildoors"',
                         'description': 'В магазинах "Profildoors" Вы найдете межкомнатные двери любого цвета, размера, структуры и различных типов открывания"', }]
                   }

    data['yml_catalog']['shop']['collections'] = collections_pd

def edit_offers_pd(dict_w_data, categories):
    for offer in dict_w_data['yml_catalog']['shop']['offers']['offer']:
        if offer['categoryId'] in ('2259', '2261', '2231', '2230', '2229', '2228', '2227'):
            dict_w_data['yml_catalog']['shop']['offers']['offer'].pop(offer)

        description = []

        typeprefix = categories[offer['categoryId']]
        offer['typePrefix'] = typeprefix
        description.append(typeprefix + '.')

        offer['collectionId'] = 'komnatnie'

        for param in offer['param']:
            if param['@name'] == 'Модель':
                offer['model'] = param['#text']

            if param['@name'] == 'Размер':
                size = param['#text'] + '.'
                description.append('Размер:')
                description.append(size)

            if param['@name'] == 'Покрытие':
                cover = param['#text'] + '.'
                description.append('Покрытие:')
                description.append(cover)

            if param['@name'] == 'Вид':
                type = param['#text'] + '.'
                description.append('Вид:')
                description.append(type)

            if param['@name'] == 'Системы открывания':
                openin = param['#text']

                if openin == 'Invisible':
                    openin = 'Скрытого монтажа'
                if openin == 'РОТО':
                    openin = 'Поворотная'
                if openin == 'Купе':
                    openin = 'Раздвижная'

                param['#text'] = openin

                openin = param['#text'] + '.'
                description.append('Тип открывания:')
                description.append(openin)

            if param['@name'] == 'Уплотнитель':
                sealer = param['#text'] + '.'
                description.append('Уплотнитель:')
                description.append(sealer)

            if param['@name'] == 'Толщина':
                fat = param['#text'] + '.'
                description.append('Толщина:')
                description.append(fat)

            if param['@name'] == 'Сталь':
                steel = param['#text'] + '.'
                description.append('Сталь:')
                description.append(steel)

            if param['@name'] == 'Замки':
                locks = param['#text'] + '.'
                description.append('Замки:')
                description.append(locks)

        description = ' '.join(description)
        offer['description'] = description

    return dict_w_data

def write_dict(dict_w_data, path):
    with open(path, 'w', encoding='UTF-8') as file:
        yml = xmltodict.unparse(dict_w_data)
        file.write(yml)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':


    # профильдорс

    data = get_dict('pd.xml')

    clear_currencies(data)

    cur_categories = get_categories(data)

    data, cat_from_child, cat_from_parent, parent_cat = clear_categories(data)

    cat_to_go = ['1', '2']
    cat_to_erase = ['5', '6', '38', '170', '314']

    for key, value in cat_from_parent.items():
        if key == '1' or key == '2':
            cat_to_go.extend(value)
        else:
            cat_to_erase.append(key)
            cat_to_erase.extend(value)

    clear_doors_categories(data)

    phone = data['yml_catalog']['shop'].pop('phone')
    print(phone)

    filter_sale(data)

    edit_offers_doors(data, cur_categories)

    write_dict(data, output_file)
    write_xml(output_file, ftp_pd)

    # риалдор
    get_xml(url_rd)

    data = get_dict(input_file)

    clear_currencies(data)

    cur_categories = get_categories(data)

    data, cat_from_child, cat_from_parent, parent_cat = clear_categories(data)

    cat_to_go = ['1', '2']
    cat_to_erase = ['5', '6', '38', '170', '314']

    for key, value in cat_from_parent.items():
        if key == '1' or key == '2':
            cat_to_go.extend(value)
        else:
            cat_to_erase.append(key)
            cat_to_erase.extend(value)

    clear_doors_categories(data)

    phone = data['yml_catalog']['shop'].pop('phone')
    print(phone)

    collections_rd = {'collection':
                       [{'@id': 'vhodnie', 'url': 'https://realdoor.ru/catalog/vhodnye-dveri/',
                         'picture': 'https://realdoor.ru/media/288/288497.png',
                         'name': 'Входные двери в магазинах "Настоящие двери"',
                         'description': 'Большой выбор входных дверей различных уровней защиты и вариантов внутренней отделки в магазинах "Настоящие двери"', },
                       {'@id': 'komnatnie', 'url': 'https://realdoor.ru/catalog/mezhkomnatnye-dveri/',
                         'picture': 'https://realdoor.ru/media/431/431589.png',
                         'name': 'Межкомнатные двери в магазинах "Настоящие двери"',
                         'description': 'В магазинах "Настоящие двери" Вы найдете межкомнатные двери любого цвета, размера, структуры и различных типов открывания', }]
                   }

    data['yml_catalog']['shop']['collections'] = collections_rd

    filter_doors_rd(data, cat_to_go, cat_to_erase, cat_from_child)

    filter_doors_colors(data)

    edit_offers_doors(data, cur_categories)

    write_dict(data, output_file)
    write_xml(output_file, ftp_rd)

    # слонпаркет
    get_xml(url)
    data = get_dict(input_file)

    cur_categories = get_categories(data)

    phone = data['yml_catalog']['shop'].pop('phone')
    print(phone)

    collections_sp = {'collection':
                       [{'@id': 'pvkh-pokrytiya', 'url': 'https://slonparket.ru/catalog/pvkh-pokrytiya/',
                         'picture': 'https://slonparket.ru/media/149/149391.jpg',
                         'name': 'Кварцвиниловая плитка (SPC, ПВХ) в магазинах "СлонПаркет"',
                         'description': 'Большой выбор кварцвинила для квартиры, дома и офиса. Качественные напольные покрытия по'
                                        ' доступным ценам. Доставка по Санкт-Петербургу и ЛО.'},
                        {'@id': 'laminat', 'url': 'https://slonparket.ru/catalog/laminat/',
                         'picture': 'https://slonparket.ru/media/128/128765.jpg',
                         'name': 'Ламинат в магазинах "СлонПаркет"',
                         'description': 'Большой выбор ламината для квартиры, дома и офиса. Качественные напольные покрытия по'
                                        ' доступным ценам. Доставка по Санкт-Петербургу и ЛО.'},
                        {'@id': 'parket', 'url': 'https://slonparket.ru/parket/',
                         'picture': 'https://slonparket.ru/media/121/121491.jpeg',
                         'name': 'Паркетная доска в магазинах "СлонПаркет"',
                         'description': 'Большой выбор паркетной доски для квартиры, дома и офиса. Качественные напольные покрытия по'
                                        ' доступным ценам. Доставка по Санкт-Петербургу и ЛО.'},
                        {'@id': 'inzhenernaya-doska', 'url': 'https://slonparket.ru/catalog/inzhenernaya-doska/',
                         'picture': 'https://slonparket.ru/media/133/133671.jpg',
                         'name': 'Инженерная доска в магазинах "СлонПаркет"',
                         'description': 'Большой выбор инженерной доски для квартиры, дома и офиса. Качественные напольные покрытия по'
                                        ' доступным ценам. Доставка по Санкт-Петербургу и ЛО.'},
                        {'@id': 'modulnyy-parket', 'url': 'https://slonparket.ru/catalog/modulnyy-parket/',
                         'picture': 'https://slonparket.ru/media/110/110576.jpg',
                         'name': 'Модульный паркет в магазинах "СлонПаркет"',
                         'description': 'Большой выбор модульного паркета для квартиры, дома и офиса. Качественные напольные покрытия по'
                                        ' доступным ценам. Доставка по Санкт-Петербургу и ЛО.'},
                        {'@id': 'probkovye-pokrytiya', 'url': 'https://slonparket.ru/catalog/probkovye-pokrytiya/',
                         'picture': 'https://slonparket.ru/media/102/102464.jpg',
                         'name': 'Пробковый пол в магазинах "СлонПаркет"',
                         'description': 'Большой выбор пробковых покрытий для квартиры, дома и офиса. Качественные напольные покрытия по'
                                        ' доступным ценам. Доставка по Санкт-Петербургу и ЛО.'},
                        {'@id': 'massivnaya-doska', 'url': 'https://slonparket.ru/catalog/massivnaya-doska/',
                         'picture': 'https://slonparket.ru/media/112/112445.jpg',
                         'name': 'Массивная доска в магазинах "СлонПаркет"',
                         'description': 'Большой выбор массивной доски для квартиры, дома и офиса. Качественные напольные покрытия по'
                                        ' доступным ценам. Доставка по Санкт-Петербургу и ЛО.'},
                        {'@id': 'terrasnaya-doska', 'url': 'https://slonparket.ru/catalog/terrasnaya-doska/',
                         'picture': 'https://slonparket.ru/media/929/92934.jpg',
                         'name': 'Террасная доска в магазинах "СлонПаркет"',
                         'description': 'Террасная доска для квартиры, дома и офиса. Качественные напольные покрытия по'
                                        ' доступным ценам. Доставка по Санкт-Петербургу и ЛО.'},
                        {'@id': 'accessories', 'url': 'https://slonparket.ru/catalog/accessories/',
                         'picture': 'https://slonparket.ru/media/153/153742.jpg',
                         'name': 'Аксессуары для напольных покрытий в магазинах "СлонПаркет"',
                         'description': 'Большой выбор аксессуаров для напольных покрытий. Качественные напольные покрытия по'
                                        ' доступным ценам. Доставка по Санкт-Петербургу и ЛО.'},
                        {'@id': 'plintusy', 'url': 'https://slonparket.ru/accessories/plintusy/',
                         'picture': 'https://slonparket.ru/media/102/102298.jpg',
                         'name': 'Плинтусы и МДФ плинтусы в магазинах "СлонПаркет"',
                         'description': 'Большой выбор плинтусов для напольных покрытий. Качественные напольные покрытия по'
                                        ' доступным ценам. Доставка по Санкт-Петербургу и ЛО.'}
                        ]
                    }


    data['yml_catalog']['shop']['collections'] = collections_sp

    set_collections(data, collection_eq_sp)

    edit_offers(data, cur_categories)

    write_dict(data, output_file)
    write_xml(output_file, ftp)

    # центрпаркета
    get_xml(url_cp1)
    data = get_dict(input_file)

    cur_categories = get_categories(data)

    phone = data['yml_catalog']['shop'].pop('phone')
    print(phone)

    edit_offers(data, cur_categories)

    write_dict(data, output_file)
    write_xml(output_file, ftp_cp1)

    if 1 == 2:

        # спбламинат
        get_xml(url_spbl)
        data = get_dict(input_file)

        cur_categories = get_categories(data)

        phone = data['yml_catalog']['shop'].pop('phone')
        print(phone)

        edit_offers(data, cur_categories)

        write_dict(data, output_file)
        write_xml(output_file, ftp_spbl)


    # ленплитка
    # with requests.Session() as session:
    #     session.headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    #     session.headers['User-Agent'] = 'Mozilla/5.0 (X11; Linux x86_64; rv:64.0) Gecko/20100101 Firefox/64.0'
    #     response = session.get(url_lenp)
    #
    #     with open(input_file, "wb") as file:
    #         file.write(response.content)
    #
    # data = get_dict(input_file)
    #
    # cur_categories = get_categories(data)
    #
    # phone = data['yml_catalog']['shop'].pop('phone')
    # print(phone)
    #
    # edit_offers_pl(data, cur_categories)
    #
    # write_dict(data, output_file)
    # write_xml(output_file, ftp_lenp)
