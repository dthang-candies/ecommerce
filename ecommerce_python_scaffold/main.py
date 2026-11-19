from domain.entities import Product
from domain.enums import ProductStatus


def main():
    # Smoke test tối thiểu cho domain model
    product = Product(
        product_id="P001",
        name="Demo product",
        description="Sản phẩm minh họa",
        price=100_000,
        stock_quantity=5,
        status=ProductStatus.ACTIVE,
    )
    print(f"{product.name}: visible={product.is_visible()}, in_stock={product.in_stock()}")


if __name__ == "__main__":
    main()
