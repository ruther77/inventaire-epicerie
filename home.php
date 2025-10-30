<?php
require_once __DIR__ . '/../config/app.php';
require_once APP_ROOT . '/DAO/DAO.php';
require_once APP_ROOT . '/Metier/produit.php';
require_once APP_ROOT . '/Metier/categorie.php';

$title = 'Home';
$dao = new DAO();
$trendingProducts = $dao->getTrendingProducts(5);
$categorySections = Categorie::afficher();

include __DIR__ . '/pages/header.php';
?>


    <!-- ----------------------------------------------------------------------------------------- -->
    <!--                                          Container                                        -->
    <!-- ----------------------------------------------------------------------------------------- -->

<div class="content-wrapper container ">
                
    <div class="page-content">
        <div id="carouselExampleSlidesOnly" class="carousel slide mb-5" data-bs-ride="carousel" data-bs-interval="2000">
        <div class="carousel-inner">
            <div class="carousel-item">
            <img src="<?= asset('assets/images/Atlas-Gaming-MSI-Laptop-Banners.jpg') ?>" class="d-block w-100" alt="...">
          </div>
          <div class="carousel-item active">
              <img src="<?= asset('assets/images/AORUS-MOTHERBOARDS-DESKTOP.jpg') ?>" class="d-block w-100" alt="...">
            </div>
        </div>
      </div>

      
<section>
    <div class="row">
        <div class="col-lg-5 m-auto text-center">
            <div class="section-title" style="margin-bottom: 10px;">
                <h2 class="h3">PRODUITS POPULAIRES</h2>
                
            </div>
        </div>
    </div>

    <div class="row">
        <div class="col-12">
            <div class="product-wrapper">
                <div class="product-carousel slick-initialized slick-slider">
                    <!-- Start Product Item -->
                    <div class="slick-list draggable">
                        <div class="slick-track pt-3" style="opacity: 1; width: 1480px; transform: translate3d(0px, 0px, 0px);">
                        <?php foreach ($trendingProducts as $index => $product): ?>
                            <div class="product-item slick-slide slick-active " data-slick-index="<?= $index ?>" aria-hidden="false" style="width: 266px;" tabindex="0">
                                <div class="product-item__thumb">
                                    <a href="<?= url_for('Customer/single-product.php?ref=' . urlencode($product->get('r'))) ?>" tabindex="0">
                                        <img class="thumb-primary" src="<?= asset('assets/photos/' . $product->get('i')) ?>" alt="Product">
                                        <img class="thumb-secondary" src="<?= asset('assets/photos/' . $product->get('i')) ?>" alt="Product">
                                    </a>
                                </div>

                                <div class="product-item__content" style="background-color:#f1f1f1;">
                                    <h4 class="title"><a href="<?= url_for('Customer/single-product.php?ref=' . urlencode($product->get('r'))) ?>" tabindex="0"><?= htmlspecialchars($product->get('l'), ENT_QUOTES, 'UTF-8') ?></a></h4>
                                    <span class="price"><strong>Price:</strong> <?= number_format((float) $product->get('p'), 2, '.', ' ') ?> Dhs</span>
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
                    <!-- End Product Item -->
                </div>
            </div>
        </div>
    </div>
</section>
<?php foreach ($categorySections as $category): ?>

<hr class="mb-5" style="background-color:gray;"/>

<section>
    <div class="row">
        <div class="col-lg-5 ml-5">
            <div class="section-title d-flex" style="margin-bottom: 10px;align-items:center">
                <h4 class="h4"><?= htmlspecialchars($category->get('n'), ENT_QUOTES, 'UTF-8') ?></h4>
                <em><a href="<?= url_for('Customer/shop.php?id=' . urlencode($category->get('n'))) ?>">Voir Plus</a></em>
            </div>
        </div>
    </div>

    <div class="row">
        <div class="col-12">
            <div class="product-wrapper">
                <div class="product-carousel slick-initialized slick-slider">
                    <!-- Start Product Item -->
                    <div class="slick-list draggable">
                        <div class="slick-track pt-3" style="opacity: 1; width: 1480px; transform: translate3d(0px, 0px, 0px);">
                        <?php
                                $productsByCategory = DAO::afficherProduitsByCat((int) $category->get('i'));
                                foreach ($productsByCategory as $index => $product) :
                        ?>
                            <div class="product-item slick-slide slick-active " data-slick-index="<?= $index ?>" aria-hidden="false" style="width: 266px;" tabindex="0">
                                <div class="product-item__thumb">
                                    <a href="<?= url_for('Customer/single-product.php?ref=' . urlencode($product->get('r'))) ?>" tabindex="0">
                                        <img class="thumb-primary" src="<?= asset('assets/photos/' . $product->get('i')) ?>" alt="Product">
                                        <img class="thumb-secondary" src="<?= asset('assets/photos/' . $product->get('i')) ?>" alt="Product">
                                    </a>
                                </div>

                                <div class="product-item__content" style="background-color:#f1f1f1;">
                                    <h4 class="title"><a href="<?= url_for('Customer/single-product.php?ref=' . urlencode($product->get('r'))) ?>" tabindex="0"><?= htmlspecialchars($product->get('l'), ENT_QUOTES, 'UTF-8') ?></a></h4>
                                    <span class="price"><strong>Price:</strong> <?= number_format((float) $product->get('p'), 2, '.', ' ') ?> Dhs</span>
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
                    <!-- End Product Item -->
                </div>
            </div>
        </div>
    </div>
</section>
<?php endforeach; ?>




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
