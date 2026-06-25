import os
import re

def fix_cart_screen():
    path = 'lib/screens/cart_screen.dart'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Add missing imports
    if 'import ''../core/design_system.dart'';' not in content:
        content = "import 'package:shopper_mobile/l10n/app_localizations.dart';\nimport '../core/design_system.dart';\nimport '../widgets/index.dart';\n" + content

    content = content.replace("import 'package:flutter_gen/gen_l10n/app_localizations.dart';", "")

    # Fix empty state
    content = re.sub(
        r'ShopperEmptyState\(\s*icon:\s*Icons\.shopping_cart_outlined,\s*message:\s*l10n\.cartEmpty,\s*actionLabel:\s*l10n\.goToProducts,\s*onAction:\s*\(\)\s*=>\s*Navigator\.pushNamed\(context,\s*AppRouter\.products\),\s*\)',
        '''ShopperEmptyState(title: l10n.cart, icon: Icons.shopping_cart_outlined, message: l10n.cartEmpty, action: ShopperPrimaryButton(text: l10n.goToProducts, onPressed: () => Navigator.pushNamed(context, AppRouter.products)))''',
        content
    )

    # Fix margin on ShopperCard
    content = content.replace(
        "ShopperCard(\n                        margin: const EdgeInsets.only(bottom: kSpacing16),",
        "Padding(padding: const EdgeInsets.only(bottom: kSpacing16), child: ShopperCard("
    )
    # Add closing ) for padding
    content = content.replace(
        "                        ),\n                      );\n                    },",
        "                        ),\n                      )));\n                    },"
    )

    # Fix quantity selector
    content = re.sub(
        r'ShopperQuantitySelector\(\s*quantity:\s*item\.quantity,\s*onPlus:.*?\),',
        '''ShopperQuantitySelector(quantity: item.quantity, onChanged: (val) { if (val == 0) { context.read<CartBloc>().add(ItemRemovedFromCart(item.id)); } else { context.read<CartBloc>().add(CartItemUpdated(cartItemId: item.id, quantity: val)); } }),''',
        content, flags=re.DOTALL
    )

    content = content.replace("item.productName", "item.product.displayName")
    content = content.replace("cart.taxAmount", "0.0")
    content = content.replace("ShopperCard(\n                  margin: EdgeInsets.zero,", "ShopperCard(")
    content = content.replace("ShopperErrorText(state.message)", "ShopperErrorText(error: state.message)")

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def fix_settings_bloc():
    path = 'lib/core/bloc/settings/settings_bloc.dart'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = content.replace("failure.errors.isNotEmpty ?", "failure.errors?.isNotEmpty == true ?")
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

fix_cart_screen()
fix_settings_bloc()
