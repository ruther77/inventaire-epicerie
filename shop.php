<?php
require_once __DIR__ . '/app.php';
require_once APP_ROOT . '/Metier/produit.php';
require_once APP_ROOT . '/Metier/categorie.php';

$title = 'Boutique';
$products = Produit::afficher();
$categoryList = Categorie::afficher();
$currentCategory = isset($_GET['id']) ? (string) $_GET['id'] : null;
$searchQuery = isset($_GET['q']) ? trim((string) $_GET['q']) : '';

include __DIR__ . '/header.php';
?>

<div class="content-wrapper container">
    <div class="page-content">
        <section class="shop-context">
        <div class="container container-wide">
            <nav aria-label="breadcrumb" class="shop-breadcrumb">
                <ol class="breadcrumb mb-3">
                    <li class="breadcrumb-item"><a href="<?= url_for('Customer/home.php') ?>">Accueil</a></li>
                    <li class="breadcrumb-item"><a href="<?= url_for('Customer/shop.php') ?>">Boutique</a></li>
                    <?php if ($currentCategory): ?>
                        <li class="breadcrumb-item active" aria-current="page">Catégorie : <?= htmlspecialchars($currentCategory, ENT_QUOTES, 'UTF-8') ?></li>
                    <?php elseif ($searchQuery !== ''): ?>
                        <li class="breadcrumb-item active" aria-current="page">Recherche : <?= htmlspecialchars($searchQuery, ENT_QUOTES, 'UTF-8') ?></li>
                    <?php else: ?>
                        <li class="breadcrumb-item active" aria-current="page">Aperçu</li>
                    <?php endif; ?>
                </ol>
            </nav>
            <div class="shop-context__header">
                <div>
                    <h1 class="h3 mb-1">Parcourez le catalogue</h1>
                    <p class="text-muted mb-0">Utilisez les onglets contextuels pour alterner entre promotions, top ventes et familles de produits.</p>
                </div>
                <div data-pinned-summary></div>
            </div>
            <div class="shop-context__tabs">
                <button class="context-tab active" type="button" data-context-tab="all">Tous</button>
                <button class="context-tab" type="button" data-context-tab="promo">Promotions</button>
                <button class="context-tab" type="button" data-context-tab="top">Top ventes</button>
                <button class="context-tab" type="button" data-context-tab="nouveau">Nouveautés</button>
                <?php foreach ($categoryList as $category): ?>
                    <button class="context-tab" type="button" data-context-tab="<?= htmlspecialchars($category->get('n'), ENT_QUOTES, 'UTF-8') ?>">
                        <?= htmlspecialchars($category->get('n'), ENT_QUOTES, 'UTF-8') ?>
                    </button>
                <?php endforeach; ?>
            </div>
            <div class="shop-context__saved-searches">
                <span class="text-muted small">Recherches enregistrées</span>
                <div class="saved-search-chips" data-saved-searches></div>
            </div>
        </div>
    </section>

        <div class="shop-page-action-bar mb-30">
            <div class="container container-wide">
                <div class="action-bar-inner">
                <div class="row align-items-center g-3">
                    <div class="col-12 col-lg-7">
                        <div class="shop-filter-pills" data-filter-pills>
                            <button class="filter-pill active" type="button" data-filter="all">Toutes les catégories</button>
                            <button class="filter-pill" type="button" data-filter="promo">Promotions</button>
                            <button class="filter-pill" type="button" data-filter="top">Top ventes</button>
                            <button class="filter-pill" type="button" data-filter="nouveau">Nouveautés</button>
                            <?php foreach ($categoryList as $category): ?>
                                <button class="filter-pill" type="button" data-filter="<?= htmlspecialchars($category->get('n'), ENT_QUOTES, 'UTF-8') ?>">
                                    <?= htmlspecialchars($category->get('n'), ENT_QUOTES, 'UTF-8') ?>
                                </button>
                            <?php endforeach; ?>
                        </div>
                    </div>
                    <div class="col-12 col-lg-3">
                        <div class="shop-layout-switcher d-flex align-items-center gap-2 justify-content-lg-end">
                            <span class="text-muted small">Affichage</span>
                            <ul class="layout-switcher nav">
                                <li class="switchergrid active" data-layout="grid"><i class="fa fa-th"></i></li>
                                <li class="switcherlist" data-layout="layout-list"><i class="fa fa-th-list"></i></li>
                            </ul>
                        </div>
                    </div>
                    <div class="col-12 col-lg-2">
                        <div class="sort-by-wrapper">
                            <label for="sort" class="sr-only">Trier par</label>
                            <select name="sort" id="sort" class="nice-select">
                                <option value="sbp">Popularité</option>
                                <option value="sbn">Nouveautés</option>
                                <option value="sbt">Tendance</option>
                                <option value="sbr">Mieux notés</option>
                            </select>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

        <div class="shop-page-product">
            <div class="container container-wide">
                <div class="product-wrapper product-layout layout-grid" id="trg">
                <div class="row mtn-30" id="products">
                    <?php foreach ($products as $index => $product): ?>
                        <?php
                            $categoryName = $product->get('c');
                            $tags = [];
                            if ($index % 3 === 0) {
                                $tags[] = 'promo';
                            }
                            if ($index % 4 === 0) {
                                $tags[] = 'top';
                            }
                            if ($index % 5 === 0) {
                                $tags[] = 'nouveau';
                                $tags[] = 'new';
                            }
                            $tagString = implode(',', $tags);
                        ?>
                        <div class="col-xl-2" data-product-card data-category="<?= htmlspecialchars($categoryName, ENT_QUOTES, 'UTF-8') ?>" data-tags="<?= htmlspecialchars($tagString, ENT_QUOTES, 'UTF-8') ?>">
                            <div class="product-item">
                                <div class="product-item__thumb">
                                    <a href="<?= url_for('Customer/single-product.php?ref=' . urlencode($product->get('r'))) ?>">
                                        <img class="thumb-primary" src="<?= asset('assets/photos/' . $product->get('i')) ?>" alt="Produit">
                                        <img class="thumb-secondary" src="<?= asset('assets/photos/' . $product->get('i')) ?>" alt="Produit">
                                    </a>
                                </div>

                                <div class="product-item__content">
                                    <div class="product-item__info">
                                        <h4 class="title" style="margin-top:15px;">
                                            <a href="<?= url_for('Customer/single-product.php?ref=' . urlencode($product->get('r'))) ?>">
                                                <?= htmlspecialchars($product->get('l'), ENT_QUOTES, 'UTF-8') ?>
                                            </a>
                                        </h4>
                                        <span class="price"><strong>Prix :</strong> <?= number_format((float) $product->get('p'), 2, '.', ' ') ?> Dhs</span>
                                    </div>

                                    <div class="product-item__action">
                                        <button class="btn-add-to-cart"><i class="ion-bag"></i></button>
                                        <button class="btn-add-to-cart"><i class="ion-ios-loop-strong"></i></button>
                                        <button class="btn-add-to-cart"><i class="ion-ios-heart-outline"></i></button>
                                        <button class="btn-add-to-cart"><i class="ion-eye"></i></button>
                                    </div>

                                    <div class="product-item__desc">
                                        <p>Poursuivez vos découvertes : comparez, enregistrez et commandez en quelques secondes.</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    <?php endforeach; ?>
                </div>
            </div>
        </div>
    </div>

        <div class="shop-page-action-bar mt-30">
            <div class="container container-wide">
                <div class="action-bar-inner">
                <div class="row align-items-center">
                    <div class="col-sm-6">
                        <nav class="pagination-wrap mb-10 mb-sm-0">
                            <ul class="pagination">
                                <li class="active"><a href="#">1</a></li>
                                <li><a href="#">2</a></li>
                                <li><a href="#">3</a></li>
                                <li><a href="#"><i class="ion-ios-arrow-thin-right"></i></a></li>
                            </ul>
                        </nav>
                    </div>
                    <div class="col-sm-6 text-center text-sm-right">
                        <p><?= count($products) ?> résultats</p>
                    </div>
                </div>
            </div>
        </div>
    </div>

<?php include __DIR__ . '/Customer/footer.php'; ?>
