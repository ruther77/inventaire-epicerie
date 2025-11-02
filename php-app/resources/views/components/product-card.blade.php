<div class="rounded-lg border border-slate-200 bg-white shadow-sm overflow-hidden">
    <div class="p-4">
        <h3 class="text-lg font-semibold text-slate-900 mb-2">{{ $product['name'] }}</h3>
        <p class="text-sm text-slate-600 mb-4">{{ $product['description'] }}</p>
        <div class="flex items-center justify-between">
            <span class="text-xl font-bold text-emerald-600">€{{ number_format($product['price'], 2, ',', ' ') }}</span>
            <span class="text-xs uppercase tracking-wide text-slate-400">{{ $product['category'] }}</span>
        </div>
    </div>
    <div class="bg-slate-50 px-4 py-3 flex items-center justify-between">
        <a href="/catalog/{{ $product['slug'] }}" class="text-sm text-emerald-700 font-medium">{{ trans('messages.view_details') }}</a>
        <form method="post" action="/cart" class="flex items-center gap-2">
            @csrf
            <input type="hidden" name="product" value="{{ $product['slug'] }}">
            <input type="number" name="quantity" value="1" min="1" class="w-16 border rounded-md px-2 py-1 text-sm">
            <button type="submit" class="px-3 py-1.5 bg-emerald-600 text-white text-sm font-medium rounded-md hover:bg-emerald-700">{{ trans('messages.add_to_cart') }}</button>
        </form>
    </div>
</div>
