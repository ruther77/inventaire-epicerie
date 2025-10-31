<?php
require_once __DIR__ . '/app.php';
require_once APP_ROOT . '/Metier/produit.php';

$reference = isset($_GET['ref']) ? (string) $_GET['ref'] : '';
$dao = new DAO();
$product = $reference !== '' ? $dao->getProduit($reference) : null;

if ($product === null) {
    http_response_code(404);
    $title = 'Produit introuvable';
    include __DIR__ . '/header.php';
    ?>
    <div class="content-wrapper container">
        <div class="page-content">
            <div class="alert alert-danger mt-5" role="alert">
                Le produit demandé est introuvable.
            </div>
        </div>

    <?php include __DIR__ . '/Customer/footer.php'; ?>
    <?php
    exit;
}

$title = $product->get('l');
include __DIR__ . '/header.php';

$relatedProducts = array_filter(
    Produit::afficher(),
    static fn (Produit $item): bool => $item->get('r') !== $product->get('r')
);
?>

    <div class="content-wrapper container">
        <div class="product-details-page-content">
            <div class="container container-wide">
                <div class="row">
                    <div class="col-12">
                        <div class="row">
                            <div class="col-md-5">
                                <div class="product-thumb-area">
                                    <div class="product-details-thumbnail" id="thumb-gallery">
                                        <figure class="pro-thumb-item">
                                            <img src="<?= asset('assets/photos/' . $product->get('i')) ?>" alt="<?= htmlspecialchars($product->get('l'), ENT_QUOTES, 'UTF-8') ?>">
                                        </figure>
                                    </div>
                                    <div class="product-details-thumbnail-nav">
                                        <?php for ($i = 0; $i < 4; $i++): ?>
                                            <figure class="pro-thumb-item">
                                                <img src="<?= asset('assets/photos/' . $product->get('i')) ?>" alt="<?= htmlspecialchars($product->get('l'), ENT_QUOTES, 'UTF-8') ?>">
                                            </figure>
                                        <?php endfor; ?>
                                    </div>
                                </div>
                            </div>

                            <div class="col-md-7">
                                <div class="product-details-info-content-wrap">
                                    <div class="prod-details-info-content">
                                        <h2><?= htmlspecialchars($product->get('l'), ENT_QUOTES, 'UTF-8') ?></h2>
                                        <h5 class="price"><strong>Price:</strong> <span class="price-amount"><?= number_format((float) $product->get('p'), 2, '.', ' ') ?> Dhs</span></h5>
                                        <p>Description non disponible.</p>

                                        <div class="product-config">
                                            <div class="table-responsive">
                                                <table class="table table-bordered">
                                                    <tbody>
                                                        <tr>
                                                            <th class="config-label">Catégorie</th>
                                                            <td class="config-option"><?= htmlspecialchars($product->get('c'), ENT_QUOTES, 'UTF-8') ?></td>
                                                        </tr>
                                                        <tr>
                                                            <th class="config-label">Stock</th>
                                                            <td class="config-option"><?= (int) $product->get('q') ?></td>
                                                        </tr>
                                                    </tbody>
                                                </table>
                                            </div>
                                        </div>

                                        <div class="product-action">
                                            <div class="action-top d-sm-flex">
                                                <div class="pro-qty mr-3 mb-4 mb-sm-0">
                                                    <label for="quantity" class="sr-only">Quantity</label>
                                                    <input type="text" id="quantity" title="Quantity" value="1">
                                                    <a href="#" class="inc qty-btn">+</a>
                                                    <a href="#" class="dec qty-btn">-</a>
                                                </div>
                                                <button class="btn btn-bordered">Add to Cart</button>
                                            </div>
                                        </div>

                                        <div class="product-meta">
                                            <span class="sku_wrapper">SKU: <span class="sku">N/A</span></span>
                                            <span class="posted_in">Catégorie: <?= htmlspecialchars($product->get('c'), ENT_QUOTES, 'UTF-8') ?></span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="row mt-5">
                            <div class="col-12">
                                <div class="product-description-review">
                                    <ul class="nav nav-tabs desc-review-tab-menu" id="desc-review-tab" role="tablist">
                                        <li>
                                            <a class="active" id="desc-tab" data-toggle="tab" href="#descriptionContent" role="tab">Description</a>
                                        </li>
                                    </ul>

                                    <div class="tab-content" id="myTabContent">
                                        <div class="tab-pane fade show active" id="descriptionContent">
                                            <div class="description-content">
                                                <p>Description non disponible.</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="shop-page-product mt-5">
            <div class="container container-wide">
                <h3>Produits associés</h3>
                <div class="product-wrapper product-layout layout-grid">
                    <div class="row mtn-30">
                        <?php foreach (array_slice($relatedProducts, 0, 4) as $related): ?>
                            <div class="col-sm-6 col-lg-4 col-xl-3">
                                <div class="product-item">
                                    <div class="product-item__thumb">
                                        <a href="<?= url_for('Customer/single-product.php?ref=' . urlencode($related->get('r'))) ?>">
                                            <img class="thumb-primary" src="<?= asset('assets/photos/' . $related->get('i')) ?>" alt="Product">
                                            <img class="thumb-secondary" src="<?= asset('assets/photos/' . $related->get('i')) ?>" alt="Product">
                                        </a>
                                    </div>

                                    <div class="product-item__content">
                                        <div class="product-item__info">
                                            <h4 class="title" style="margin-top:15px;">
                                                <a href="<?= url_for('Customer/single-product.php?ref=' . urlencode($related->get('r'))) ?>">
                                                    <?= htmlspecialchars($related->get('l'), ENT_QUOTES, 'UTF-8') ?>
                                                </a>
                                            </h4>
                                            <span class="price"><strong>Price:</strong> <?= number_format((float) $related->get('p'), 2, '.', ' ') ?> Dhs</span>
                                        </div>

                                        <div class="product-item__action">
                                            <button class="btn-add-to-cart"><i class="ion-bag"></i></button>
                                            <button class="btn-add-to-cart"><i class="ion-ios-loop-strong"></i></button>
                                            <button class="btn-add-to-cart"><i class="ion-ios-heart-outline"></i></button>
                                            <button class="btn-add-to-cart"><i class="ion-eye"></i></button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        <?php endforeach; ?>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <?php include __DIR__ . '/Customer/footer.php'; ?>
