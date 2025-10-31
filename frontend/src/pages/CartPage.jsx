const CART_LINES = [
  { id: 1, name: 'Pommes Golden', qty: 3, price: 2.4 },
  { id: 2, name: 'Yaourt nature', qty: 6, price: 0.9 },
];

export default function CartPage() {
  const total = CART_LINES.reduce((sum, line) => sum + line.qty * line.price, 0);

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Compte</p>
          <h1>Panier</h1>
          <p className="page-description">Retrouvez votre panier quelle que soit la session ou l&apos;appareil.</p>
        </div>
        <div className="page-badges">
          <span className="badge badge-count">{CART_LINES.length}</span>
        </div>
      </header>
      <section className="card">
        <h2>Résumé</h2>
        <ul className="cart-list">
          {CART_LINES.map((line) => (
            <li key={line.id}>
              <div>
                <strong>{line.name}</strong>
                <span>× {line.qty}</span>
              </div>
              <span>{(line.qty * line.price).toFixed(2)} €</span>
            </li>
          ))}
        </ul>
        <p className="cart-total">Total: {total.toFixed(2)} €</p>
      </section>
    </div>
  );
}
