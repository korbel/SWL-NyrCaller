import com.GameInterface.Game.Character;
import com.GameInterface.Game.Dynel;
import com.GameInterface.Log;
import com.GameInterface.Tooltip.TooltipData;
import com.GameInterface.Tooltip.TooltipDataProvider;
import com.Utils.ID32;

import lp.nyr10caller.utils.ArrayUtils;

class lp.nyr10caller.CharacterSubscription {

    private static var s_subscriptions:Object = new Object();

    private var m_character:Character;

    private var m_statFilter:Array;
    private var m_buffFilter:Array;

    // statFilter, buffFilter explanation: id of stats and id of buffs to subscribe for. if null, there're no restrictions, if empty array it won't subscribe
    public static function Add(dynel:Dynel, shouldLogCommands:Boolean, statFilter:Array, buffFilter:Array) {
        var dynelID:ID32 = dynel.GetID();

        if (dynelID.GetType() != _global.Enums.TypeID.e_Type_GC_Character) {
            return;
        }

        if (s_subscriptions[dynelID.toString()]) {
            return;
        }

        var sub = new CharacterSubscription(Character.GetCharacter(dynelID), statFilter, buffFilter);
        sub.Subscribe(shouldLogCommands);
        s_subscriptions[dynelID.toString()] = sub;
    }

    public static function Remove(dynel:Dynel) {
        var dynelID:ID32 = dynel.GetID();

        if (dynelID.GetType() != _global.Enums.TypeID.e_Type_GC_Character) {
            return;
        }

        var sub = s_subscriptions[dynelID.toString()];

        if (!sub) {
            return;
        }

        sub.Unubscribe();
        delete s_subscriptions[dynelID.toString()];
    }

    private function CharacterSubscription(character:Character, statFilter:Array, buffFilter:Array) {
        m_character = character;
        m_statFilter = statFilter;
        m_buffFilter = buffFilter;
    }

    private function Subscribe(shouldLogCommands:Boolean) {
        m_character.SignalCharacterDied.Connect(CharacterDied, this);
        m_character.SignalCharacterAlive.Connect(CharacterAlive, this);

        if (!m_buffFilter || m_buffFilter.length > 0) {
            m_character.SignalBuffAdded.Connect(BuffAdded, this);
            m_character.SignalBuffRemoved.Connect(BuffRemoved, this);
            m_character.SignalBuffUpdated.Connect(BuffUpdated, this);
            m_character.SignalInvisibleBuffAdded.Connect(InvisibleBuffAdded, this);
            m_character.SignalInvisibleBuffUpdated.Connect(InvisibleBuffUpdated, this);
        }

        if (!m_statFilter || m_statFilter.lenth > 0) {
            m_character.SignalStatChanged.Connect(StatChanged, this);
        }

        if (shouldLogCommands) {
            m_character.SignalCommandStarted.Connect(CommandStarted, this);
            m_character.SignalCommandEnded.Connect(CommandEnded, this);
            m_character.SignalCommandAborted.Connect(CommandAborted, this);
        }

        m_character.ConnectToCommandQueue();

        Log.Error("Nyr10Caller", "DynelSubscribed: " + m_character.GetID() + "|" + m_character.GetName());
    }

    private function Unubscribe() {
        m_character.SignalCharacterDied.Disconnect(CharacterDied, this);
        m_character.SignalCharacterAlive.Disconnect(CharacterAlive, this);

        m_character.SignalBuffAdded.Disconnect(BuffAdded, this);
        m_character.SignalBuffRemoved.Disconnect(BuffRemoved, this);
        m_character.SignalBuffUpdated.Disconnect(BuffUpdated, this);
        m_character.SignalInvisibleBuffAdded.Disconnect(InvisibleBuffAdded, this);
        m_character.SignalInvisibleBuffUpdated.Disconnect(InvisibleBuffUpdated, this);

        m_character.SignalStatChanged.Disconnect(StatChanged, this);

        m_character.SignalCommandStarted.Disconnect(CommandStarted, this);
        m_character.SignalCommandEnded.Disconnect(CommandEnded, this);
        m_character.SignalCommandAborted.Disconnect(CommandAborted, this);

        Log.Error("Nyr10Caller", "DynelUnsubscribed: " + m_character.GetID());
    }



    private function StatChanged(statID:Number) {
        if (!m_statFilter || ArrayUtils.Contains(m_statFilter, statID)) {
            Log.Error("Nyr10Caller", "StatChanged: " + m_character.GetID() + "|" + statID + "|" + m_character.GetStat(statID));
        }
    }



    private function CharacterDied() {
        Log.Error("Nyr10Caller", "CharacterDied: " + m_character.GetID());
    }

    private function CharacterAlive() {
        Log.Error("Nyr10Caller", "CharacterAlive: " + m_character.GetID());
    }



    private function BuffAdded(buffId:Number) {
        if (!m_buffFilter || ArrayUtils.Contains(m_buffFilter, buffId)) {
            var tooltip:TooltipData = TooltipDataProvider.GetBuffTooltip(buffId, m_character.GetID());
            Log.Error("Nyr10Caller", "BuffAdded: " + m_character.GetID() + "|" + buffId + "|" + tooltip.m_Title);
        }
    }

    private function BuffRemoved(buffId:Number) {
        if (!m_buffFilter || ArrayUtils.Contains(m_buffFilter, buffId)) {
            Log.Error("Nyr10Caller", "BuffRemoved: " + m_character.GetID() + "|" + buffId);
        }
    }

    private function BuffUpdated(buffId:Number) {
        if (!m_buffFilter || ArrayUtils.Contains(m_buffFilter, buffId)) {
            Log.Error("Nyr10Caller", "BuffUpdated: " + m_character.GetID() + "|" + buffId);
        }
    }

    private function InvisibleBuffAdded(buffId:Number) {
        if (!m_buffFilter || ArrayUtils.Contains(m_buffFilter, buffId)) {
            var tooltip:TooltipData = TooltipDataProvider.GetBuffTooltip(buffId, m_character.GetID());
            Log.Error("Nyr10Caller", "InvisibleBuffAdded: " + m_character.GetID() + "|" + buffId + "|" + tooltip.m_Title);
        }
    }

    private function InvisibleBuffUpdated(buffId:Number) {
        if (!m_buffFilter || ArrayUtils.Contains(m_buffFilter, buffId)) {
            Log.Error("Nyr10Caller", "InvisibleBuffUpdated: " + m_character.GetID() + "|" + buffId);
        }
    }



    private function CommandStarted(name:String, progressBarType:Number, uninterruptable:Boolean) {
        Log.Error("Nyr10Caller", "CommandStarted: " + m_character.GetID() + "|" + name);
    }

    private function CommandEnded() {
        Log.Error("Nyr10Caller", "CommandEnded: " + m_character.GetID());
    }

    private function CommandAborted() {
        Log.Error("Nyr10Caller", "CommandAborted: " + m_character.GetID());
    }

}
