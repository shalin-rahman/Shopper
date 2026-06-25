import os

def fix_cart_screen():
    path = 'lib/screens/cart_screen.dart'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'import ''../core/design_system.dart'';' not in content:
        content = ""import 'package:shopper_mobile/l10n/app_localizations.dart';\nimport '../core/design_system.dart';\nimport '../widgets/index.dart';\n"" + content

    content = content.replace(
        ""ShopperEmptyState(\n                icon: Icons.shopping_cart_outlined,\n                message: l10n.cartEmpty,\n                actionLabel: l10n.goToProducts,\n                onAction: () => Navigator.pushNamed(context, AppRouter.products),\n              );"",
        ""ShopperEmptyState(\n                title: l10n.cart,\n                icon: Icons.shopping_cart_outlined,\n                message: l10n.cartEmpty,\n                action: ShopperPrimaryButton(\n                  text: l10n.goToProducts,\n                  onPressed: () => Navigator.pushNamed(context, AppRouter.products),\n                ),\n              );""
    )
    
    content = content.replace(
        ""ShopperCard(\n                        margin: const EdgeInsets.only(bottom: kSpacing16),\n                        child: Padding(\n                          padding: const EdgeInsets.all(kSpacing12),"",
        ""Padding(\n                        padding: const EdgeInsets.only(bottom: kSpacing16),\n                        child: ShopperCard(\n                          child: Padding(\n                            padding: const EdgeInsets.all(kSpacing12),""
    )
    
    content = content.replace(
        ""ShopperQuantitySelector(\n                                quantity: item.quantity,\n                                onPlus: () {\n                                  context.read<CartBloc>().add(CartItemUpdated(\n                                    cartItemId: item.id,\n                                    quantity: item.quantity + 1,\n                                  ));\n                                },\n                                onMinus: () {\n                                  if (item.quantity > 1) {\n                                    context.read<CartBloc>().add(CartItemUpdated(\n                                      cartItemId: item.id,\n                                      quantity: item.quantity - 1,\n                                    ));\n                                  } else {\n                                    context.read<CartBloc>().add(ItemRemovedFromCart(item.id));\n                                  }\n                                },\n                              ),"",
        ""ShopperQuantitySelector(\n                                quantity: item.quantity,\n                                onChanged: (val) {\n                                  if (val == 0) {\n                                    context.read<CartBloc>().add(ItemRemovedFromCart(item.id));\n                                  } else {\n                                    context.read<CartBloc>().add(CartItemUpdated(\n                                      cartItemId: item.id,\n                                      quantity: val,\n                                    ));\n                                  }\n                                },\n                              ),""
    )
    
    content = content.replace(
        ""                      );\n                    },"",
        ""                        ),\n                      ));\n                    },""
    )
    
    content = content.replace(""item.productName"", ""item.product.displayName"")
    content = content.replace(""cart.taxAmount"", ""0.0"")
    content = content.replace(""ShopperCard(\n                  margin: EdgeInsets.zero,\n                  padding: const EdgeInsets.all(kSpacing24),"", ""ShopperCard(\n                  padding: const EdgeInsets.all(kSpacing24),"")
    content = content.replace(""ShopperErrorText(state.message)"", ""ShopperErrorText(error: state.message)"")
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

fix_cart_screen()
