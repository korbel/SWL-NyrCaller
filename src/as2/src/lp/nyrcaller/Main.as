import com.GameInterface.Game.Character;
import com.GameInterface.Game.Dynel;
import com.GameInterface.Nametags;
import com.GameInterface.Log;
import com.GameInterface.WaypointInterface;
import com.Utils.ID32;
import com.Utils.LDBFormat;
import mx.utils.Delegate;

import lp.nyrcaller.utils.ArrayUtils;
import lp.nyrcaller.CharacterSubscription;

class lp.nyrcaller.Main {

    private static var s_app:Main;

    private static var NYR10_PLAYFIELD_ID:Number = 5715;
    private static var LURKER_NAME = "The Unutterable Lurker"; // TODO: make these compatible with non-english clients
    private static var WATCHED_ENEMY_NPCS:Array = ["Zero-Point Titan", "Eldritch Guardian", "Mouths of Montauk"]
    private static var WATCHED_ALLY_NPCS = ["Alex", "Mei Ling", "Rose"]

    private var m_swfRoot:MovieClip;
    private var m_dynels:Array;

    private var m_initialized:Boolean;

    public static function main(swfRoot:MovieClip) {
        s_app = new Main(swfRoot);

        swfRoot.onLoad = function() {
            Main.s_app.OnLoad();
        };
        swfRoot.OnUnload = function() {
            Main.s_app.OnUnload();
        };
    }

    public function Main(swfRoot:MovieClip) {
        m_swfRoot = swfRoot;
    }

    public function OnLoad() {
        m_initialized = false;

        m_swfRoot.onEnterFrame = Delegate.create(this, OnFrame);
    }

    public function OnUnload() {
        m_swfRoot.onEnterFrame = undefined;

        Nametags.SignalNametagAdded.Disconnect(Add, this);
        Nametags.SignalNametagRemoved.Disconnect(Add, this);
        Nametags.SignalNametagUpdated.Disconnect(Add, this);

        WaypointInterface.SignalPlayfieldChanged.Disconnect(PlayFieldChanged, this);

        for (var i in m_dynels) {
            Remove(m_dynels[i].GetID());
        }

        m_initialized = false;
    }

    public function Init() {
        m_dynels = new Array();

        Nametags.SignalNametagAdded.Connect(Add, this);
        Nametags.SignalNametagRemoved.Connect(Add, this);
        Nametags.SignalNametagUpdated.Connect(Add, this);
        Nametags.RefreshNametags();

        WaypointInterface.SignalPlayfieldChanged.Connect(PlayFieldChanged, this);
        PlayFieldChanged(Character.GetClientCharacter().GetPlayfieldID());

        m_initialized = true;
    }

    private function OnFrame() {
        if (!m_initialized) {
            Init();
        }

        for (var i in m_dynels) {
            var dynel:Dynel = m_dynels[i];
            if (!ShouldWatch(dynel)) {
                Remove(dynel.GetID());
                return;
            }
        }
    }

    private function Add(id:ID32) {


        var dynel:Dynel = Dynel.GetDynel(id);

        if (ArrayUtils.Contains(m_dynels, dynel) || !ShouldWatch(dynel)) {
            return
        }

        var name:String = dynel.GetName();

        if (ArrayUtils.Contains(WATCHED_ENEMY_NPCS, name)) {
            m_dynels.push(dynel);
            CharacterSubscription.Add(dynel, true, null, []);
        } else if (ArrayUtils.Contains(WATCHED_ALLY_NPCS, name)) {
            m_dynels.push(dynel);
            CharacterSubscription.Add(dynel, false, [], [8907544, 8907521]); // XX_Ally Knockdown 1, Inevitable Doom
        } else if (dynel.GetID().IsPlayer()) {
            m_dynels.push(dynel);
            CharacterSubscription.Add(dynel, false, [], [8907521, 9125195, 8907522]); // Inevitable Doom, Whisper of Darkness, Rumblings Below
        } else if (name == LURKER_NAME && dynel.GetStat(421)) { // stat(421) == 27 No idea what this stat is but it seems to be specific to "real" lurker
            m_dynels.push(dynel);
            CharacterSubscription.Add(dynel, true);
        }
    }

    private function Remove(id:ID32) {
        var dynel:Dynel = Dynel.GetDynel(id);

        ArrayUtils.Remove(m_dynels, dynel);
        CharacterSubscription.Remove(dynel);
    }

    private function ShouldWatch(dynel:Dynel):Boolean {
        if (Character.GetClientCharacter().GetPlayfieldID() != NYR10_PLAYFIELD_ID) {
            return false;
        }

        if (Character.GetClientCharID().Equal(dynel.GetID())) {
            return true;
        }

        if (!dynel.GetID().IsPlayer() && (!dynel.GetDistanceToPlayer() || dynel.IsDead())) {
            return false;
        }

        return true;
    }

    private function PlayFieldChanged(newPlayfield:Number) {
        //for (var i in m_dynels) {
        //Remove(m_dynels[i].GetID());
        //}
        Log.Error("NyrCaller", "PlayFieldChanged: " + newPlayfield + "|" + LDBFormat.LDBGetText("Playfieldnames", newPlayfield));

    }

}
