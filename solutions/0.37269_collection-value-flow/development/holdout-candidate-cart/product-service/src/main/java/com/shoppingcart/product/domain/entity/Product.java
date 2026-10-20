package com.shoppingcart.product.domain.entity;

import com.shoppingcart.product.domain.vo.Category;
import com.shoppingcart.product.domain.vo.Money;
import com.shoppingcart.product.domain.vo.ProductId;
import com.shoppingcart.product.domain.vo.ProductImage;

/**
 * Represents a product in the shopping cart system.
 * 
 * This class encapsulates product information including identity, pricing,
 * description, category, and image details. It uses value objects to ensure
 * type safety and domain-driven design principles.
 * 
 * The Product class is immutable and provides factory methods for reconstruction
 * from persisted data.
 * 
 * @author Shopping Cart Team
 */
public class Product {

    private final ProductId id;
    private final String title;
    private final Money price;
    private final String description;
    private final Category category;
    private final ProductImage image;

    /**
     * Private constructor to create a Product instance.
     * 
     * This constructor is private to enforce the use of factory methods for
     * instance creation, ensuring consistent object initialization.
     * 
     * @param id the unique product identifier
     * @param title the product title
     * @param price the product price as a Money value object
     * @param description the product description
     * @param category the product category
     * @param image the product image information
     */
    private Product(ProductId id, String title, Money price,
            String description, Category category, ProductImage image) {
        this.id = id;
        this.title = title;
        this.price = price;
        this.description = description;
        this.category = category;
        this.image = image;
    }

    /**
     * Factory method to reconstitute a Product from persisted data.
     * 
     * This method creates a Product instance from individual data fields,
     * typically used when loading products from a database.
     * 
     * @param id the product identifier as a Long value
     * @param title the product title
     * @param price the product price as a double value
     * @param description the product description
     * @param category the product category as a String
     * @param imageUrl the URL of the product image
     * @return a new Product instance with the specified data
     */
    public static Product reconstitute(Long id, String title, double price,
            String description, String category, String imageUrl) {
        return new Product(
                new ProductId(id),
                title,
                Money.of(price),
                description,
                new Category(category),
                new ProductImage(imageUrl));
    }

    /**
     * Gets the product's unique identifier.
     * 
     * @return the ProductId value object representing this product's unique identifier
     */
    public ProductId getId() {
        return id;
    }

    /**
     * Gets the product's title.
     * 
     * @return the product title
     */
    public String getTitle() {
        return title;
    }

    /**
     * Gets the product's price.
     * 
     * @return the product price as a Money value object
     */
    public Money getPrice() {
        return price;
    }

    /**
     * Gets the product's description.
     * 
     * @return the product description
     */
    public String getDescription() {
        return description;
    }

    /**
     * Gets the product's category.
     * 
     * @return the product category as a Category value object
     */
    public Category getCategory() {
        return category;
    }

    /**
     * Gets the product's image information.
     * 
     * @return the product image as a ProductImage value object
     */
    public ProductImage getImage() {
        return image;
    }
}
