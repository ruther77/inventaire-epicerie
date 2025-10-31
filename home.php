<?php
require_once __DIR__ . '/app.php';
require_once APP_ROOT . '/DAO/DAO.php';
require_once APP_ROOT . '/Metier/produit.php';
require_once APP_ROOT . '/Metier/categorie.php';

$title = 'Accueil';
$dao = new DAO();
$trendingProducts = $dao->getTrendingProducts(5);
$categorySections = Categorie::afficher();
$suggestedCategories = array_slice($categorySections, 0, 6);

include __DIR__ . '/header.php';
?>

<div class="content-wrapper container">
    <div class="page-content">
        <section class="home-hero">
            <div class="row align-items-center g-4">
                <div class="col-lg-7">
                    <span class="home-hero__eyebrow">Bienvenue chez Jellouli</span>
                    <h1 class="display-6">Planifiez vos courses sans multiplier les onglets</h1>
                    <p class="lead">Retrouvez produits, commandes et promotions depuis un point d'entrée unique. Commencez par rechercher une inspiration ou explorez nos catégories les plus consultées.</p>
                    <form class="home-hero__search" action="<?= url_for('Customer/shop.php') ?>" method="get">
                        <label class="visually-hidden" for="homeSearch">Rechercher un produit</label>
                        <div class="input-group input-group-lg">
                            <span class="input-group-text"><i class="bi bi-search"></i></span>
                            <input id="homeSearch" class="form-control" type="search" name="q" placeholder="Rechercher un produit, une marque, une catégorie…">
                            <button class="btn btn-primary" type="submit">Chercher</button>
                        </div>
                    </form>
                    <div class="home-hero__quick-links">
                        <?php foreach ($suggestedCategories as $category): ?>
                            <a class="quick-link-chip" href="<?= url_for('Customer/shop.php?id=' . urlencode($category->get('n'))) ?>">
                                <i class="bi bi-tag"></i>
                                <?= htmlspecialchars($category->get('n'), ENT_QUOTES, 'UTF-8') ?>
                            </a>
                        <?php endforeach; ?>
                    </div>
                    <div class="home-hero__insight">
                        <i class="bi bi-lightning-charge-fill text-warning"></i>
                        <span>Astuce : épinglez vos sections favorites depuis le menu « Catalogue » pour y accéder plus vite.</span>
                    </div>
                    <div class="mt-3">
                        <span class="text-muted small d-block mb-1">Vos recherches enregistrées</span>
                        <div class="saved-search-chips" data-saved-searches data-placeholder="false"></div>
                    </div>
                </div>
                <div class="col-lg-5">
                    <div class="card border-0 shadow-sm">
                        <img src="<?= asset('assets/images/AORUS-MOTHERBOARDS-DESKTOP.jpg') ?>" class="card-img-top" alt="Promotion de saison">
                        <div class="card-body">
                            <p class="text-uppercase text-muted small mb-1">Promotion du moment</p>
                            <h2 class="h5">-20% sur les indispensables petit-déjeuner</h2>
                            <p class="text-muted mb-0">Profitez-en avant le 30 avril et ajoutez vos favoris d'un geste.</p>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <section class="home-actions">
            <h2 class="section-title">Que souhaitez-vous faire ?</h2>
            <div class="row g-4">
                <div class="col-12 col-md-6 col-xl-3">
                    <article class="action-card">
                        <h3 class="h5">Acheter</h3>
                        <p>Choisissez vos produits et remplissez votre panier en quelques clics.</p>
                        <a class="action-card__link" href="<?= url_for('Customer/shop.php') ?>">Explorer la boutique <i class="bi bi-arrow-up-right"></i></a>
                    </article>
                </div>
                <div class="col-12 col-md-6 col-xl-3">
                    <article class="action-card">
                        <h3 class="h5">Consulter mes commandes</h3>
                        <p>Suivez l'état de vos commandes et téléchargez vos factures à tout moment.</p>
                        <a class="action-card__link" href="<?= url_for('Customer/orders.php') ?>">Accéder à l'historique <i class="bi bi-arrow-up-right"></i></a>
                    </article>
                </div>
                <div class="col-12 col-md-6 col-xl-3">
                    <article class="action-card">
                        <h3 class="h5">Promotions</h3>
                        <p>Découvrez nos sélections du moment et les ventes flash à ne pas manquer.</p>
                        <a class="action-card__link" href="<?= url_for('Customer/shop.php?promo=1') ?>">Voir les offres <i class="bi bi-arrow-up-right"></i></a>
                    </article>
                </div>
                <div class="col-12 col-md-6 col-xl-3">
                    <article class="action-card">
                        <h3 class="h5">Aide</h3>
                        <p>Besoin d'un coup de main ? Contactez l'équipe ou parcourez notre centre d'aide.</p>
                        <a class="action-card__link" href="<?= url_for('Customer/support.php') ?>">Obtenir de l'aide <i class="bi bi-arrow-up-right"></i></a>
                    </article>
                </div>
            </div>
        </section>

        <section class="home-highlights">
            <div class="row g-4 align-items-center">
                <div class="col-lg-7">
                    <div class="highlight-card">
                        <h2 class="h4 mb-2">Produits populaires</h2>
                        <p class="text-muted mb-0">Une sélection mise à jour automatiquement selon les meilleures ventes du moment.</p>
                    </div>
                </div>
                <div class="col-lg-5">
                    <div class="highlight-card">
                        <h3 class="h6 mb-1">Filtrez en un clic</h3>
                        <p class="text-muted mb-0">Utilisez les filtres contextuels depuis la boutique pour alterner entre catégories, promos et top ventes.</p>
                    </div>
                </div>
            </div>
            <div class="product-wrapper mt-4">
                <div class="product-carousel slick-initialized slick-slider">
                    <div class="slick-list draggable">
                        <div class="slick-track pt-3" style="opacity: 1; width: 1480px; transform: translate3d(0px, 0px, 0px);">
                            <?php foreach ($trendingProducts as $index => $product): ?>
                                <div class="product-item slick-slide slick-active" data-slick-index="<?= $index ?>" aria-hidden="false" style="width: 266px;" tabindex="0">
                                    <div class="product-item__thumb">
                                        <a href="<?= url_for('Customer/single-product.php?ref=' . urlencode($product->get('r'))) ?>" tabindex="0">
                                            <img class="thumb-primary" src="<?= asset('assets/photos/' . $product->get('i')) ?>" alt="Produit">
                                            <img class="thumb-secondary" src="<?= asset('assets/photos/' . $product->get('i')) ?>" alt="Produit">
                                        </a>
                                    </div>
                                    <div class="product-item__content home-product-card">
                                        <h4 class="title"><a href="<?= url_for('Customer/single-product.php?ref=' . urlencode($product->get('r'))) ?>" tabindex="0"><?= htmlspecialchars($product->get('l'), ENT_QUOTES, 'UTF-8') ?></a></h4>
                                        <span class="price"><strong>Prix :</strong> <?= number_format((float) $product->get('p'), 2, '.', ' ') ?> Dhs</span>
                                    </div>
                                    <div class="product-item__action">
                                        <button class="btn-add-to-cart" tabindex="0"><i class="ion-bag"></i></button>
                                        <button class="btn-add-to-cart" tabindex="0"><i class="ion-ios-loop-strong"></i></button>
                                        <button class="btn-add-to-cart" tabindex="0"><i class="ion-ios-heart-outline"></i></button>
                                        <button class="btn-add-to-cart" tabindex="0"><i class="ion-eye"></i></button>
                                    </div>
                                </div>
                            <?php endforeach; ?>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <?php foreach ($categorySections as $category): ?>
            <section class="home-category">
                <div class="d-flex flex-column flex-md-row justify-content-between align-items-md-center mb-3 gap-3">
                    <div>
                        <h3 class="h4 mb-1"><?= htmlspecialchars($category->get('n'), ENT_QUOTES, 'UTF-8') ?></h3>
                        <p class="text-muted mb-0">Les incontournables de la catégorie, prêts à être ajoutés à votre panier.</p>
                    </div>
                    <div class="home-category__actions">
                        <a class="btn btn-outline-secondary btn-sm" href="<?= url_for('Customer/shop.php?id=' . urlencode($category->get('n'))) ?>">Tout voir</a>
                        <a class="btn btn-link btn-sm text-decoration-none" href="<?= url_for('Customer/shop.php?id=' . urlencode($category->get('n'))) ?>">
                            <i class="bi bi-funnel me-1"></i>Filtrer dans la boutique
                        </a>
                    </div>
                </div>
                <div class="product-wrapper">
                    <div class="product-carousel slick-initialized slick-slider">
                        <div class="slick-list draggable">
                            <div class="slick-track pt-3" style="opacity: 1; width: 1480px; transform: translate3d(0px, 0px, 0px);">
                                <?php
                                    $productsByCategory = DAO::afficherProduitsByCat((int) $category->get('i'));
                                    foreach ($productsByCategory as $index => $product):
                                ?>
                                    <div class="product-item slick-slide slick-active" data-slick-index="<?= $index ?>" aria-hidden="false" style="width: 266px;" tabindex="0">
                                        <div class="product-item__thumb">
                                            <a href="<?= url_for('Customer/single-product.php?ref=' . urlencode($product->get('r'))) ?>" tabindex="0">
                                                <img class="thumb-primary" src="<?= asset('assets/photos/' . $product->get('i')) ?>" alt="Produit">
                                                <img class="thumb-secondary" src="<?= asset('assets/photos/' . $product->get('i')) ?>" alt="Produit">
                                            </a>
                                        </div>
                                        <div class="product-item__content home-product-card">
                                            <h4 class="title"><a href="<?= url_for('Customer/single-product.php?ref=' . urlencode($product->get('r'))) ?>" tabindex="0"><?= htmlspecialchars($product->get('l'), ENT_QUOTES, 'UTF-8') ?></a></h4>
                                            <span class="price"><strong>Prix :</strong> <?= number_format((float) $product->get('p'), 2, '.', ' ') ?> Dhs</span>
                                        </div>
                                        <div class="product-item__action">
                                            <button class="btn-add-to-cart" tabindex="0"><i class="ion-bag"></i></button>
                                            <button class="btn-add-to-cart" tabindex="0"><i class="ion-ios-loop-strong"></i></button>
                                            <button class="btn-add-to-cart" tabindex="0"><i class="ion-ios-heart-outline"></i></button>
                                            <button class="btn-add-to-cart" tabindex="0"><i class="ion-eye"></i></button>
                                        </div>
                                    </div>
                                <?php endforeach; ?>
                            </div>
                        </div>
                    </div>
                </div>
            </section>
        <?php endforeach; ?>

        <section class="home-dashboard-teaser">
            <div class="row align-items-center g-4">
                <div class="col-lg-8">
                    <h2 class="h3 mb-2">Un centre de contrôle pour vos équipes internes</h2>
                    <p class="mb-0">Suivez l'inventaire, les commandes et les analyses depuis un tableau de bord dédié. Chaque carte mène vers une vue spécialisée.</p>
                </div>
                <div class="col-lg-4 text-lg-end">
                    <a class="btn btn-light" href="<?= url_for('Customer/dashboard.php') ?>">Ouvrir le tableau de bord</a>
                </div>
            </div>
        </section>
    </div>

<?php include __DIR__ . '/Customer/footer.php'; ?>
