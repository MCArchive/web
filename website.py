from metafile import load_mods

from flask import Flask, render_template, abort
app = Flask(__name__)

app.mods = load_mods('repo/mods')

# This adds utility functions to the template engine.
@app.context_processor
def utility_funcs():
    def url_type_name(ty):
        if ty == 'archived': return 'Archived File'
        elif ty == 'original': return 'Official Download'
        elif ty == 'page': return 'Official Download Page'
        else: return ty
    return dict(
        url_type_name=url_type_name
    )

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/mods/')
def mod_list():
    return render_template('mods.html', mods=app.mods)

@app.route('/mods/<id>')
def mod_page(id):
    if id in app.mods:
        mod = app.mods[id]
        return render_template('mod.html', mod=mod)
    else: abort(404)
