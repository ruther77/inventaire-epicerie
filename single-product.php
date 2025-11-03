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
                <div class="product-details-shell" role="main" aria-labelledby="productTitle">
                    <div class="row g-5">
                        <div class="col-lg-5">
                            <div class="product-gallery atlas-card" data-component="gallery">
                                <div class="product-gallery__focus">
                                    <img src="<?= asset('assets/photos/' . $product->get('i')) ?>" alt="<?= htmlspecialchars($product->get('l'), ENT_QUOTES, 'UTF-8') ?>" loading="lazy">
                                </div>
                                <div class="product-gallery__thumbnails" role="list">
                                    <?php for ($i = 0; $i < 4; $i++): ?>
                                        <button class="product-gallery__thumbnail" type="button" role="listitem" aria-label="Voir la photo <?= $i + 1 ?> de <?= htmlspecialchars($product->get('l'), ENT_QUOTES, 'UTF-8') ?>">
                                            <img src="<?= asset('assets/photos/' . $product->get('i')) ?>" alt="Aperçu <?= $i + 1 ?>" loading="lazy">
                                        </button>
                                    <?php endfor; ?>
                                </div>
                            </div>
                        </div>

                        <div class="col-lg-7">
                            <article class="product-summary atlas-card" aria-labelledby="productTitle">
                                <header class="product-summary__header">
                                    <h1 class="product-summary__title" id="productTitle"><?= htmlspecialchars($product->get('l'), ENT_QUOTES, 'UTF-8') ?></h1>
                                    <p class="product-summary__price">Prix&nbsp;: <strong><?= number_format((float) $product->get('p'), 2, '.', ' ') ?>&nbsp;Dhs</strong></p>
                                </header>
                                <p class="product-summary__description">Description non disponible.</p>

                                <dl class="product-summary__meta">
                                    <div>
                                        <dt>Catégorie</dt>
                                        <dd><?= htmlspecialchars($product->get('c'), ENT_QUOTES, 'UTF-8') ?></dd>
                                    </div>
                                    <div>
                                        <dt>Stock disponible</dt>
                                        <dd><?= (int) $product->get('q') ?></dd>
                                    </div>
                                </dl>

                                <div class="product-summary__actions">
                                    <div class="product-quantity-control" role="group" aria-label="Choisir la quantité">
                                        <button class="product-quantity-control__btn" type="button" data-qty-action="decrement" aria-label="Diminuer la quantité">
                                            <span aria-hidden="true">−</span>
                                        </button>
                                        <label class="visually-hidden" for="quantity">Quantité</label>
                                        <input class="product-quantity-control__input" type="number" id="quantity" name="quantity" min="1" value="1" inputmode="numeric">
                                        <button class="product-quantity-control__btn" type="button" data-qty-action="increment" aria-label="Augmenter la quantité">
                                            <span aria-hidden="true">+</span>
                                        </button>
                                    </div>
                                    <button class="atlas-btn" type="button">Ajouter au panier</button>
                                </div>

                                <footer class="product-summary__footer">
                                    <span class="product-summary__sku">SKU&nbsp;: <span>N/A</span></span>
                                    <span class="product-summary__category">Catégorie&nbsp;: <?= htmlspecialchars($product->get('c'), ENT_QUOTES, 'UTF-8') ?></span>
                                </footer>
                            </article>
                        </div>
                    </div>

                    <div class="row mt-5">
                        <div class="col-12">
                            <section class="product-description atlas-card" aria-labelledby="productDescriptionTab">
                                <div class="product-description__tabs" role="tablist">
                                    <button class="product-description__tab active" id="productDescriptionTab" type="button" role="tab" aria-selected="true" aria-controls="productDescriptionPanel">Description</button>
                                </div>
                                <div class="product-description__panels">
                                    <div class="product-description__panel show" id="productDescriptionPanel" role="tabpanel" aria-labelledby="productDescriptionTab">
                                        <p>Description non disponible.</p>
                                    </div>
                                </div>
                            </section>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="shop-page-product mt-5">
            <div class="container container-wide">
                <h2 class="h3">Produits associés</h2>
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
                                            <span class="price"><strong>Prix&nbsp;:</strong> <?= number_format((float) $related->get('p'), 2, '.', ' ') ?> Dhs</span>
                                        </div>

                                        <div class="product-item__action" role="group" aria-label="Actions rapides">
                                            <button class="btn-add-to-cart" type="button" aria-label="Ajouter <?= htmlspecialchars($related->get('l'), ENT_QUOTES, 'UTF-8') ?> au panier">
                                                <i class="ion-bag" aria-hidden="true"></i>
                                            </button>
                                            <button class="btn-add-to-cart" type="button" aria-label="Comparer <?= htmlspecialchars($related->get('l'), ENT_QUOTES, 'UTF-8') ?>">
                                                <i class="ion-ios-loop-strong" aria-hidden="true"></i>
                                            </button>
                                            <button class="btn-add-to-cart" type="button" aria-label="Ajouter <?= htmlspecialchars($related->get('l'), ENT_QUOTES, 'UTF-8') ?> aux favoris">
                                                <i class="ion-ios-heart-outline" aria-hidden="true"></i>
                                            </button>
                                            <button class="btn-add-to-cart" type="button" aria-label="Voir les détails de <?= htmlspecialchars($related->get('l'), ENT_QUOTES, 'UTF-8') ?>">
                                                <i class="ion-eye" aria-hidden="true"></i>
                                            </button>
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
