import os
import re

def fix_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Add missing imports
    if 'NoParams' in content and 'core/usecase/usecase.dart' not in content:
        content = "import '../../../core/usecase/usecase.dart';\n" + content
    
    if 'SearchProductsParams' in content and 'search_products_usecase.dart' not in content:
        content = "import '../../../domain/usecases/products/search_products_usecase.dart';\n" + content

    # Fix isNotEmpty nullability
    content = content.replace('failure.errors.isNotEmpty ? failure.errors.first : failure.message', 'failure.errors?.isNotEmpty == true ? failure.errors!.first : failure.message')
    content = content.replace('failure.errors.isNotEmpty ? failure.errors?.isNotEmpty == true ? failure.errors!.first : failure.message : failure.message', 'failure.errors?.isNotEmpty == true ? failure.errors!.first : failure.message')

    # Fix type inference in fold
    content = re.sub(r'\(order\)\s*=>\s*emit\(OrderCreatedSuccess', r'(dynamic order) => emit(OrderCreatedSuccess', content)
    content = re.sub(r'\(settings\)\s*=>\s*emit\(SettingsUpdatedSuccess', r'(dynamic settings) => emit(SettingsUpdatedSuccess', content)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

fix_file('lib/core/bloc/products/products_bloc.dart')
fix_file('lib/core/bloc/cart/cart_bloc.dart')
fix_file('lib/core/bloc/orders/orders_bloc.dart')
fix_file('lib/core/bloc/settings/settings_bloc.dart')
