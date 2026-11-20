/** @odoo-module **/

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

import { Component, onWillStart, useState } from "@odoo/owl";
import { getThemePref, setThemePref } from "./theme_utils";

const THEME_OPTIONS = [
    { value: "light", label: _t("Day"), icon: "sun" },
    { value: "dark", label: _t("Night"), icon: "moon" },
    { value: "auto", label: _t("Auto"), icon: "sun-moon" },
];

export class ThemeLangSystray extends Component {
    static template = "bpro_theme_switcher.ThemeLangSystray";
    static components = { Dropdown, DropdownItem };
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            themePref: getThemePref(),
            languages: [],
            currentLang: user.context.lang,
        });
        onWillStart(async () => {
            this.state.languages = await this.orm.searchRead(
                "res.lang",
                [["active", "=", true]],
                ["code", "name"]
            );
        });
    }

    get themeOptions() {
        return THEME_OPTIONS;
    }

    onSelectTheme(value) {
        this.state.themePref = value;
        setThemePref(value);
    }

    async onSelectLang(code) {
        if (code === this.state.currentLang) {
            return;
        }
        await this.orm.write("res.users", [user.userId], { lang: code });
        window.location.reload();
    }
}

export const themeLangSystrayItem = {
    Component: ThemeLangSystray,
};

registry.category("systray").add("bpro.theme_lang_systray", themeLangSystrayItem, { sequence: 1 });
