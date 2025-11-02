<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Models\ProductRepository;
use App\Support\Cart;
use Framework\Http\Response;
use Framework\Validation\Validator;

final class CartController extends Controller
{
    private Cart $cart;

    public function __construct(private readonly ProductRepository $products = new ProductRepository())
    {
        parent::__construct();
        $this->cart = new Cart();
    }

    public function index(): Response
    {
        return $this->view('pages.cart', [
            'items' => $this->cart->items(),
            'total' => $this->cart->total(),
        ]);
    }

    public function store(): Response
    {
        $request = $this->request();
        if (!$this->session()->validateCsrf($request->input('_token'))) {
            return response('CSRF token mismatch', 419);
        }
        $data = $request->only(['product', 'quantity']);
        $validator = new Validator($data);
        $errors = $validator->validate([
            'product' => 'required',
            'quantity' => 'required',
        ]);

        if ($errors !== []) {
            $this->session()->setErrors($errors);
            $this->session()->setOld($data);

            return redirect('/catalog');
        }

        $product = $this->products->findBySlug((string) $data['product']);
        if ($product === null) {
            $this->session()->setErrors(['product' => ['validation.exists']]);

            return redirect('/catalog');
        }

        $quantity = max(1, (int) $data['quantity']);
        $this->cart->add($product, $quantity);
        $this->session()->flash('status', trans('messages.cart_added', ['name' => $product['name']]));
        $this->session()->setOld([]);
        $this->session()->setErrors([]);

        return redirect('/cart');
    }

    public function destroy(): Response
    {
        if (!$this->session()->validateCsrf($this->request()->input('_token'))) {
            return response('CSRF token mismatch', 419);
        }
        $this->cart->clear();
        $this->session()->flash('status', trans('messages.cart_cleared'));

        return redirect('/cart');
    }
}
