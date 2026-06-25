import os
import re

def fix_api_client():
    path = 'lib/data/sources/remote/api_client.dart'
    if not os.path.exists(path): return
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    content = content.replace("import 'package:dartz/dartz.dart';", "import 'package:dartz/dartz.dart' hide Order;")
    content = content.replace("AppPreferences preferences;", "dynamic preferences;")
    content = content.replace("result.validate is Function", "(result as dynamic).validate is Function")
    content = content.replace("result.validate()", "(result as dynamic).validate()")
    content = content.replace("validateRequired(data,", "validateRequired(data?.toString(),")
    content = content.replace("import 'package:shopper_mobile/domain/entities/user.dart';", "import 'package:shopper_mobile/domain/entities/user.dart' hide AuthToken;")
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def fix_usecases():
    # add_to_cart
    p1 = 'lib/domain/usecases/cart/add_to_cart_usecase.dart'
    if os.path.exists(p1):
        with open(p1, 'r', encoding='utf-8') as f:
            c = f.read()
        c = c.replace("validateRequired(quantity,", "validateRequired(quantity.toString(),")
        with open(p1, 'w', encoding='utf-8') as f: f.write(c)
        
    # create_order
    p2 = 'lib/domain/usecases/orders/create_order_usecase.dart'
    if os.path.exists(p2):
        with open(p2, 'r', encoding='utf-8') as f:
            c = f.read()
        c = c.replace("validateRequired(cart,", "validateRequired(cart.items.isEmpty ? '' : 'items',")
        with open(p2, 'w', encoding='utf-8') as f: f.write(c)

    # update_settings
    p3 = 'lib/domain/usecases/settings/update_settings_usecase.dart'
    if os.path.exists(p3):
        with open(p3, 'r', encoding='utf-8') as f:
            c = f.read()
        c = c.replace("UseCase<Settings, Settings>", "UseCase<AppSettings, AppSettings>")
        c = c.replace("Future<Either<Failure, Settings>> call(Settings params)", "Future<Either<Failure, AppSettings>> call(AppSettings params)")
        with open(p3, 'w', encoding='utf-8') as f: f.write(c)

def fix_all_blocs():
    blocs = [
        'lib/core/bloc/auth/auth_bloc.dart',
        'lib/core/bloc/cart/cart_bloc.dart',
        'lib/core/bloc/products/products_bloc.dart',
        'lib/core/bloc/orders/orders_bloc.dart',
        'lib/core/bloc/settings/settings_bloc.dart'
    ]
    for p in blocs:
        if not os.path.exists(p): continue
        with open(p, 'r', encoding='utf-8') as f:
            c = f.read()

        c = c.replace("failure.errors.isNotEmpty ? failure.errors?.isNotEmpty == true ? failure.errors!.first : failure.message : failure.message", "failure.errors?.isNotEmpty == true ? failure.errors!.first : failure.message")
        c = c.replace("failure.errors.isNotEmpty ? failure.errors.first : failure.message", "failure.errors?.isNotEmpty == true ? failure.errors!.first : failure.message")
        c = c.replace("failure.errors.isNotEmpty", "(failure.errors?.isNotEmpty == true)")
        
        c = c.replace("(dynamic order) => emit", "(_) => emit")
        c = c.replace("(dynamic settings) => emit", "(_) => emit")
        c = c.replace("(order) => emit", "(_) => emit")
        c = c.replace("(settings) => emit", "(_) => emit")

        if 'NoParams' in c and 'usecase.dart' not in c:
            c = "import '../../../core/usecase/usecase.dart';\n" + c
        if 'SearchProductsParams' in c and 'search_products_usecase.dart' not in c:
            c = "import '../../../domain/usecases/products/search_products_usecase.dart';\n" + c
            
        with open(p, 'w', encoding='utf-8') as f:
            f.write(c)

fix_api_client()
fix_usecases()
fix_all_blocs()
