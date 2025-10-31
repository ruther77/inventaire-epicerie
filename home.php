<?php
require_once __DIR__ . '/../config/app.php';
require_once APP_ROOT . '/DAO/DAO.php';
require_once APP_ROOT . '/Metier/produit.php';
require_once APP_ROOT . '/Metier/categorie.php';

$title = 'Home';
$dao = new DAO();
$trendingProducts = $dao->getTrendingProducts(5);
$categorySections = Categorie::afficher();
$suggestedCategories = array_slice($categorySections, 0, 6);

include __DIR__ . '/pages/header.php';
?>


    <!-- ----------------------------------------------------------------------------------------- -->
    <!--                                          Container                                        -->
    <!-- ----------------------------------------------------------------------------------------- -->

<div class="content-wrapper container ">
                
    <div class="page-content">
        <section class="home-hero">
            <div class="row align-items-center g-4">
                <div class="col-lg-7">
                    <div class="home-hero__content">
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
                            <i class="bi bi-lightning-charge-fill text-warning me-2"></i>
                            <span>Astuce : Épinglez vos sections favorites depuis le menu « Catalogue » pour y accéder plus vite.</span>
                        </div>
                    </div>
                </div>
                <div class="col-lg-5">
                    <div id="carouselHeroHighlights" class="carousel slide home-hero__carousel" data-bs-ride="carousel" data-bs-interval="4000">
                        <div class="carousel-inner rounded-4 overflow-hidden">
                            <div class="carousel-item active">
                                <img src="<?= asset('assets/images/AORUS-MOTHERBOARDS-DESKTOP.jpg') ?>" class="d-block w-100" alt="Promotion équipement maison">
                            </div>
                            <div class="carousel-item">
                                <img src="<?= asset('assets/images/Atlas-Gaming-MSI-Laptop-Banners.jpg') ?>" class="d-block w-100" alt="Offres gaming">
                            </div>
                        </div>
                    </div>
                    <div class="home-hero__promo card shadow-sm mt-3">
                        <div class="card-body d-flex align-items-center">
                            <i class="bi bi-stars display-6 text-primary me-3"></i>
                            <div>
                                <p class="text-uppercase text-muted small mb-1">Promotion du moment</p>
                                <p class="fw-semibold mb-0">-20% sur les indispensables petit-déjeuner jusqu'au 30 avril.</p>
                            </div>
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
                        <p>Suivez l'état de vos commandes, téléchargez vos factures et planifiez vos réapprovisionnements.</p>
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
                    <div class="highlight-card shadow-sm">
                        <div>
                            <h2 class="h4 mb-2">Produits populaires</h2>
                            <p class="text-muted mb-0">Une sélection mise à jour automatiquement selon les meilleures ventes du moment.</p>
                        </div>
                        <a class="btn btn-outline-primary btn-sm" href="<?= url_for('Customer/shop.php?sort=sbt') ?>">Voir tout</a>
                    </div>
                </div>
                <div class="col-lg-5">
                    <div class="highlight-card shadow-sm">
                        <div>
                            <h2 class="h6 mb-1">Faites le tri en un clic</h2>
                            <p class="text-muted mb-0">Utilisez les filtres contextuels depuis la page boutique pour alterner entre catégories, promos et top ventes.</p>
                        </div>
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
                                        <img class="thumb-primary" src="<?= asset('assets/photos/' . $product->get('i')) ?>" alt="Product">
                                        <img class="thumb-secondary" src="<?= asset('assets/photos/' . $product->get('i')) ?>" alt="Product">
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
                    <button class="btn btn-link btn-sm text-decoration-none" type="button" data-quick-filter="<?= htmlspecialchars($category->get('n'), ENT_QUOTES, 'UTF-8') ?>">
                        <i class="bi bi-funnel me-1"></i>Filtrer sur la boutique
                    </button>
                </div>
            </div>
            <div class="product-wrapper">
                <div class="product-carousel slick-initialized slick-slider">
                    <div class="slick-list draggable">
                        <div class="slick-track pt-3" style="opacity: 1; width: 1480px; transform: translate3d(0px, 0px, 0px);">
                        <?php
                            $productsByCategory = DAO::afficherProduitsByCat((int) $category->get('i'));
                            foreach ($productsByCategory as $index => $product) :
                        ?>
                            <div class="product-item slick-slide slick-active" data-slick-index="<?= $index ?>" aria-hidden="false" style="width: 266px;" tabindex="0">
                                <div class="product-item__thumb">
                                    <a href="<?= url_for('Customer/single-product.php?ref=' . urlencode($product->get('r'))) ?>" tabindex="0">
                                        <img class="thumb-primary" src="<?= asset('assets/photos/' . $product->get('i')) ?>" alt="Product">
                                        <img class="thumb-secondary" src="<?= asset('assets/photos/' . $product->get('i')) ?>" alt="Product">
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

        <section class="home-internal-dashboard">
            <div class="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-3">
                <div>
                    <h2 class="h4 mb-1">Centre de contrôle pour l'équipe</h2>
                    <p class="text-muted mb-0">Un aperçu rapide des tâches internes pour gérer l'inventaire, les commandes et les performances.</p>
                </div>
                <a class="btn btn-primary" href="<?= url_for('Customer/dashboard.php') ?>">
                    Accéder au tableau de bord
                </a>
            </div>
            <div class="row g-4">
                <div class="col-12 col-md-4">
                    <article class="dashboard-card">
                        <h3 class="h5">Inventaire</h3>
                        <p>Consultez les niveaux de stock, les ruptures à venir et importez de nouveaux produits.</p>
                        <a class="dashboard-card__link" href="<?= url_for('Customer/dashboard.php#inventory') ?>">Ouvrir l'espace Inventaire</a>
                    </article>
                </div>
                <div class="col-12 col-md-4">
                    <article class="dashboard-card">
                        <h3 class="h5">Commandes</h3>
                        <p>Suivez l'état des commandes clients et organisez la préparation et la livraison.</p>
                        <a class="dashboard-card__link" href="<?= url_for('Customer/dashboard.php#orders') ?>">Ouvrir l'espace Commandes</a>
                    </article>
                </div>
                <div class="col-12 col-md-4">
                    <article class="dashboard-card">
                        <h3 class="h5">Analyses</h3>
                        <p>Analysez les ventes, les paniers moyens et les performances des promotions.</p>
                        <a class="dashboard-card__link" href="<?= url_for('Customer/dashboard.php#analytics') ?>">Ouvrir l'espace Analyses</a>
                    </article>
                </div>
            </div>
        </section>




            </div>
            

            <footer>
                <div class="container">
                    <div class="footer clearfix mb-0 text-muted">
                        <div class="float-start">
                            <p>2021 &copy; Mazer</p>
                        </div>
                        <div class="float-end">
                            <p>Crafted with <span class="text-danger"><i class="bi bi-heart"></i></span> by <a
                                href="https://saugi.me">Saugi</a></p>
                        </div>
                    </div>
                </div>
            </footer>
        </div>
    </div>
    </div>
    <script src="<?= asset('assets/js/bootstrap.js') ?>"></script>
    <script src="<?= asset('assets/js/app.js') ?>"></script>
    <script src="<?= asset('Customer/js.js') ?>"></script>


</body>

</html>
