import json
from django.shortcuts import render
from django.http import HttpResponse
from decimal import Decimal, getcontext
from .services.mnemonic_service import generate_mnemonics
from .services.solana_service import derive_solana_addresses

getcontext().prec = 60

# 12-word BIP39 = 128 bits of entropy = 2^128 possible unique wallets
TOTAL_POSSIBLE = 2 ** 128
TOTAL_FORMATTED = f"{TOTAL_POSSIBLE:,}"


def index(request):
    return render(request, 'solapp/index.html')


def info(request):
    return render(request, 'solapp/info.html')


def test_htmx(request):
    return HttpResponse("<p class='text-green-600 font-bold'>HTMX is working!</p>")


def generate_mnemonics_view(request):
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))

        if quantity < 1 or quantity > 100:
            return HttpResponse("<p class='text-red-600 font-bold'>Invalid quantity.</p>")

        try:
            mnemonics = generate_mnemonics(count=quantity)
        except Exception as e:
            return HttpResponse(f"<p class='text-red-600 font-bold'>Error: {str(e)}</p>")

        # --- Session tracking ---
        session_total = request.session.get('total_generated', 0) + quantity
        request.session['total_generated'] = session_total

        # --- Python does ALL the math ---
        percentage = Decimal(session_total) / Decimal(TOTAL_POSSIBLE) * Decimal(100)
        percentage_str = format(percentage, '.38f')

        # --- Mnemonics HTML ---
        mnemonics_html = ""
        for i, mnemonic in enumerate(mnemonics, 1):
            mnemonics_html += f"""
                <div class='border-2 border-black p-4 mb-3'>
                    <div class='flex justify-between items-start mb-2'>
                        <p class='text-xs font-black tracking-widest'>MNEMONIC #{i}</p>
                        <button
                            onclick="copyToClipboard('{mnemonic}', this)"
                            class='text-xs font-black tracking-widest hover:underline cursor-pointer'>
                            COPY
                        </button>
                    </div>
                    <p class='font-mono text-sm text-black break-all'>{mnemonic}</p>
                </div>
            """

        mnemonics_html += f"""
            <script>
                document.getElementById('download-btn').classList.remove('hidden');
                document.getElementById('derive-btn').classList.remove('hidden');
                sessionStorage.setItem('pendingMnemonics', JSON.stringify({json.dumps(mnemonics)}));
            </script>
        """

        # --- OOB counter chunk — HTMX swaps this into #odds-counter ---
        oob_html = f"""
            <div id="odds-counter" hx-swap-oob="true">
                <div class="grid grid-cols-1 md:grid-cols-3 gap-8 mb-8">
                    <div class="md:col-span-2">
                        <p class="text-xs font-black tracking-widest text-gray-400 mb-3">TOTAL POSSIBLE WALLETS (2¹²⁸)</p>
                        <p class="font-mono text-sm font-bold text-white break-all leading-relaxed">{TOTAL_FORMATTED}</p>
                    </div>
                    <div>
                        <p class="text-xs font-black tracking-widest text-gray-400 mb-3">GENERATED THIS SESSION</p>
                        <p class="font-mono text-5xl font-black text-white">{session_total:,}</p>
                    </div>
                </div>
                <div>
                    <p class="text-xs font-black tracking-widest text-gray-400 mb-3">YOUR COVERAGE OF THE ADDRESS SPACE</p>
                    <p class="font-mono text-base font-black text-white mb-4">{percentage_str}%</p>
                    <div class="w-full h-1 bg-gray-800">
                        <div class="h-1 bg-white" style="width: 0%"></div>
                    </div>
                    <p class="text-xs text-gray-600 mt-3 tracking-widest">THE BAR IS NOT BROKEN. YOU ARE JUST VERY SMALL.</p>
                </div>
            </div>
        """

        return HttpResponse(mnemonics_html + oob_html)

    return HttpResponse("<p class='text-red-600 font-bold'>INVALID REQUEST</p>")


def derive_view(request):
    if request.method == 'GET':
        return render(request, 'solapp/derive.html')

    if request.method == 'POST':
        source = request.POST.get('source', 'manual')

        try:
            num_accounts = int(request.POST.get('num_accounts', 1))
            num_accounts = max(1, min(10, num_accounts))
        except (ValueError, TypeError):
            num_accounts = 1

        if source == 'session':
            try:
                mnemonics = json.loads(request.POST.get('mnemonics_data', '[]'))
            except (ValueError, TypeError):
                mnemonics = []
        else:
            raw = request.POST.get('mnemonics_text', '').strip()
            mnemonics = [line.strip() for line in raw.splitlines() if line.strip()]

        if not mnemonics:
            return HttpResponse(
                "<p class='text-xs font-black tracking-widest text-red-500'>"
                "NO MNEMONICS FOUND. GENERATE SOME FIRST OR PASTE THEM MANUALLY."
                "</p>"
            )

        results = []
        for i, mnemonic in enumerate(mnemonics, 1):
            words = mnemonic.strip().split()
            if len(words) != 12:
                results.append({
                    'index': i,
                    'mnemonic': mnemonic,
                    'addresses': [],
                    'error': f'INVALID — EXPECTED 12 WORDS, GOT {len(words)}',
                })
                continue
            try:
                addresses = derive_solana_addresses(mnemonic, num_accounts)
                results.append({'index': i, 'mnemonic': mnemonic, 'addresses': addresses})
            except Exception as e:
                results.append({
                    'index': i,
                    'mnemonic': mnemonic,
                    'addresses': [],
                    'error': str(e).upper(),
                })

        return HttpResponse(_build_derive_html(results, num_accounts))

    return HttpResponse("<p class='text-red-600 font-bold'>INVALID REQUEST</p>")


def _build_derive_html(results, num_accounts):
    total = sum(len(r['addresses']) for r in results)
    errors = sum(1 for r in results if r.get('error'))
    valid_count = len(results) - errors
    accounts_used = num_accounts

    # --- Summary bar ---
    error_note = (
        f'<p class="text-xs font-black tracking-widest text-red-500 mt-1">{errors} INVALID SKIPPED</p>'
        if errors else ''
    )
    summary = f"""
    <div class="mb-4 pb-4 border-b-2 border-black">
        <p class="text-xs font-black tracking-widest">
            {total} ADDRESSES DERIVED FROM {valid_count} MNEMONIC{'S' if valid_count != 1 else ''}
        </p>
        {error_note}
    </div>
    """

    # --- Address cards ---
    cards_html = ""
    for r in results:
        if r.get('error'):
            cards_html += f"""
            <div class="border-2 border-red-300 p-4 mb-3">
                <p class="text-xs font-black tracking-widest text-red-500 mb-1">
                    MNEMONIC #{r['index']} — {r['error']}
                </p>
                <p class="font-mono text-[10px] text-gray-400 break-all">{r['mnemonic']}</p>
            </div>
            """
            continue

        addresses_html = ""
        for addr in r['addresses']:
            a = addr['address']
            p = addr['derivation_path']
            addresses_html += f"""
            <div class="bg-gray-50 border border-gray-200 px-3 py-2 flex justify-between items-start gap-4"
                 data-address="{a}" data-path="{p}">
                <div class="min-w-0">
                    <p class="text-[10px] font-black text-gray-400 tracking-widest mb-1">{p}</p>
                    <p class="font-mono text-xs font-bold break-all">{a}</p>
                </div>
                <button onclick="copyToClipboard('{a}', this)"
                        class="text-xs font-black tracking-widest hover:underline flex-shrink-0 ml-2">
                    COPY
                </button>
            </div>
            """

        safe_mnemonic = r['mnemonic'].replace("'", "\\'")
        cards_html += f"""
        <div class="border-2 border-black p-4 mb-3 mnemonic-group" data-mnemonic="{r['mnemonic']}">
            <div class="flex justify-between items-start mb-2">
                <p class="text-xs font-black tracking-widest">MNEMONIC #{r['index']}</p>
                <button onclick="copyToClipboard('{safe_mnemonic}', this)"
                        class="text-xs font-black tracking-widest hover:underline">
                    COPY PHRASE
                </button>
            </div>
            <p class="font-mono text-[10px] text-gray-400 mb-3 break-all">{r['mnemonic']}</p>
            <div class="space-y-2">{addresses_html}</div>
        </div>
        """

    # --- OOB swap: update the black stats panel ---
    path_range = f"0–{accounts_used - 1}" if accounts_used > 1 else "0"
    oob_html = f"""
    <div id="derive-stats" hx-swap-oob="true">
        <div class="grid grid-cols-2 gap-6 mb-8">
            <div>
                <p class="text-xs font-black tracking-widest text-gray-400 mb-3">MNEMONICS PROCESSED</p>
                <p class="font-mono text-5xl font-black text-white">{valid_count}</p>
            </div>
            <div>
                <p class="text-xs font-black tracking-widest text-gray-400 mb-3">ADDRESSES DERIVED</p>
                <p class="font-mono text-5xl font-black text-white">{total}</p>
            </div>
        </div>
        <div>
            <p class="text-xs font-black tracking-widest text-gray-400 mb-3">DERIVATION PATH</p>
            <p class="font-mono text-sm text-white">m/44'/501'/[{path_range}]'/0'</p>
            <p class="text-xs text-gray-600 mt-3 tracking-widest">
                SAME SEED. DIFFERENT PATHS. DIFFERENT WALLETS.
            </p>
        </div>
    </div>
    """

    # --- Reveal download button ---
    script = "<script>document.getElementById('download-all-btn').classList.remove('hidden');</script>"

    return summary + cards_html + oob_html + script
