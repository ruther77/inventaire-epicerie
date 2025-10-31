const PROMO_ITEMS = [
  { id: 1, name: 'Paniers de saison', discount: 20, validUntil: '15/07/2024' },
  { id: 2, name: 'Sélection bio', discount: 15, validUntil: '30/06/2024' },
  { id: 3, name: 'Boissons fraîches', discount: 10, validUntil: '10/08/2024' },
];

export default function PromotionsPage() {
  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Catalogue</p>
          <h1>Promotions</h1>
          <p className="page-description">
            Mettez en avant vos offres spéciales et partagez-les rapidement avec vos équipes.
          </p>
        </div>
        <div className="page-badges">
          <span className="badge badge-promo">Promo</span>
        </div>
      </header>
      <section className="card">
        <h2>Campagnes en cours</h2>
        <ul className="promo-list">
          {PROMO_ITEMS.map((item) => (
            <li key={item.id}>
              <div>
                <h3>{item.name}</h3>
                <p>Jusqu&apos;à {item.discount}% de remise</p>
              </div>
              <span className="badge badge-new">Jusqu&apos;au {item.validUntil}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
