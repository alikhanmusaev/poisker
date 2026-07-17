package ru.poisker.app.ui.icons

import androidx.annotation.DrawableRes
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Icon
import androidx.compose.material3.LocalContentColor
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import ru.poisker.app.R

object LucideIcons {
    @DrawableRes val Search = R.drawable.ic_lucide_search

    @DrawableRes val MapPin = R.drawable.ic_lucide_map_pin

    @DrawableRes val ChevronDown = R.drawable.ic_lucide_chevron_down

    @DrawableRes val LayoutGrid = R.drawable.ic_lucide_layout_grid

    @DrawableRes val Bookmark = R.drawable.ic_lucide_bookmark

    @DrawableRes val MessagesSquare = R.drawable.ic_lucide_messages_square

    @DrawableRes val Send = R.drawable.ic_lucide_send

    @DrawableRes val BookmarkCheck = R.drawable.ic_lucide_bookmark_check

    @DrawableRes val Image = R.drawable.ic_lucide_image

    @DrawableRes val Plus = R.drawable.ic_lucide_plus

    @DrawableRes val User = R.drawable.ic_lucide_user

    @DrawableRes val LogIn = R.drawable.ic_lucide_log_in

    @DrawableRes val UserPlus = R.drawable.ic_lucide_user_plus

    @DrawableRes val ArrowLeft = R.drawable.ic_lucide_arrow_left

    @DrawableRes val Pencil = R.drawable.ic_lucide_pencil

    @DrawableRes val Phone = R.drawable.ic_lucide_phone

    @DrawableRes val Share2 = R.drawable.ic_lucide_share_2

    @DrawableRes val House = R.drawable.ic_lucide_house

    @DrawableRes val Car = R.drawable.ic_lucide_car

    @DrawableRes val Cog = R.drawable.ic_lucide_cog

    @DrawableRes val Smartphone = R.drawable.ic_lucide_smartphone

    @DrawableRes val Shirt = R.drawable.ic_lucide_shirt

    @DrawableRes val ShoppingBag = R.drawable.ic_lucide_shopping_bag

    @DrawableRes val Sofa = R.drawable.ic_lucide_sofa

    @DrawableRes val Wrench = R.drawable.ic_lucide_wrench

    @DrawableRes val Briefcase = R.drawable.ic_lucide_briefcase

    @DrawableRes val Baby = R.drawable.ic_lucide_baby

    @DrawableRes val PawPrint = R.drawable.ic_lucide_paw_print

    @DrawableRes val Dumbbell = R.drawable.ic_lucide_dumbbell

    @DrawableRes val Hammer = R.drawable.ic_lucide_hammer

    @DrawableRes val Flower2 = R.drawable.ic_lucide_flower_2

    @DrawableRes val Apple = R.drawable.ic_lucide_apple

    @DrawableRes val Store = R.drawable.ic_lucide_store

    @DrawableRes
    fun category(webName: String): Int = when (webName) {
        "home" -> House
        "car" -> Car
        "cog" -> Cog
        "smartphone" -> Smartphone
        "shirt" -> Shirt
        "shopping-bag" -> ShoppingBag
        "sofa" -> Sofa
        "wrench" -> Wrench
        "briefcase" -> Briefcase
        "baby" -> Baby
        "paw-print" -> PawPrint
        "dumbbell" -> Dumbbell
        "hammer" -> Hammer
        "flower-2" -> Flower2
        "apple" -> Apple
        "store" -> Store
        "layout-grid" -> LayoutGrid
        else -> LayoutGrid
    }
}

@Composable
fun LucideIcon(
    @DrawableRes res: Int,
    contentDescription: String?,
    modifier: Modifier = Modifier,
    tint: Color = LocalContentColor.current,
) {
    Icon(
        painter = painterResource(res),
        contentDescription = contentDescription,
        // Default 24dp; caller can override with Modifier.size(...) after.
        modifier = Modifier.size(24.dp).then(modifier),
        tint = tint,
    )
}
